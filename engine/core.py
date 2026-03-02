import os
from queue import Queue
import pygame
import math
from typing import List
import shutil
import uuid

from enum import Enum
from .createBackgrounds import BackgroundCreator

class shapes(Enum):
    RECTANGLE = 1
    ELLIPSE = 2
    IMAGE = 3

class TRACK_TYPE(Enum):
    SNAP = 1
    SMOOTH = 2

shouldDebugCollisions = False

def drawShape(screen, shape, color, position, size, image: pygame.Surface | None = None, borderConfig: int | None = None):
    extra_offset = (0, 0)
    #if(tracking_type == TRACK_TYPE.SMOOTH):
    #    extra_offset = (screen_size[0] / 2, screen_size[1] / 2)

    # Handle alpha transparency
    if len(color) == 4 and color[3] < 255:
        if (color[3]) <= 0:
            return  # Fully transparent, do not draw

        # Create a temporary surface with per-pixel alpha
        temp_surface = pygame.Surface((size[0], size[1]), pygame.SRCALPHA)
        temp_surface = temp_surface.convert_alpha()
        
        if shape == shapes.RECTANGLE:
            pygame.draw.rect(temp_surface, color, (0, 0, size[0], size[1]), borderConfig if borderConfig is not None else 0)
        elif shape == shapes.ELLIPSE:
            rect = pygame.Rect(-size[0] / 2, -size[1] / 2, size[0], size[1])
            pygame.draw.ellipse(temp_surface, color, rect)

        temp_surface.fill(color, special_flags=pygame.BLEND_RGBA_MULT)

        # Blit the temporary surface to the main screen
        screen.blit(temp_surface, (position[0] + extra_offset[0], position[1] + extra_offset[1]))
    else:
        # No alpha or fully opaque, use direct drawing for better performance
        draw_color = color[:3] if len(color) == 4 else color
        
        if shape == shapes.RECTANGLE:
            pygame.draw.rect(screen, draw_color, (position[0] + extra_offset[0], position[1] + extra_offset[1], size[0], size[1]), borderConfig if borderConfig is not None else 0)
        elif shape == shapes.ELLIPSE:
            rect = pygame.Rect(position[0] - size[0] / 2 + extra_offset[0], position[1] - size[1] / 2 + extra_offset[1], size[0], size[1])
            pygame.draw.ellipse(screen, draw_color, rect)
        elif shape == shapes.IMAGE:
            # scale the image to the size of 'size'
            scaled_image = pygame.transform.scale(image, size)
            # multiply colors by 'color'
            scaled_image.fill(color, special_flags=pygame.BLEND_MULT)
            screen.blit(scaled_image, (position[0] + extra_offset[0], position[1] + extra_offset[1]))

def rect2ellipseCollision(rect: 'Core.object', ellipse: 'Core.object') -> bool:
    # Rectangle: position = [x, y] (top-left), size = [width, height]
    # Ellipse: position = [cx, cy] (center), size = [width, height] (diameters)
    rect_x, rect_y = rect.position
    rect_w, rect_h = rect.size
    ell_x, ell_y = ellipse.position
    ell_w, ell_h = ellipse.size

    global shouldDebugCollisions, debugShapes
    if(shouldDebugCollisions):
        # draw the rectangle edges
        if rect.id not in debugShapes:
            debugShapes[rect.id] = []
            rect_debug = Core.object(rect.core, shapes.RECTANGLE, (255, 0, 0, 128), [rect_x, rect_y], [rect_w, rect_h])
            rect_debug.border = 2
            debugShapes[rect.id].append(rect_debug)

        # draw the ellipse bounding box
        if ellipse.id not in debugShapes:
            debugShapes[ellipse.id] = []
            ell_debug = Core.object(ellipse.core, shapes.RECTANGLE, (0, 255, 0, 128), 
                        [ell_x - ell_w / 2, ell_y - ell_h/2], [ell_w, ell_h])
            ell_debug.border = 2
            debugShapes[ellipse.id].append(ell_debug)

        closest_x = max(rect_x, min(ell_x, rect_x + rect_w))
        closest_y = min(rect_y + rect_h, max(ell_y, rect_y))

        # draw the closest point on the rectangle
        point_debug = Core.object(ellipse.core, shapes.ELLIPSE, (0, 0, 255, 128), 
                     [closest_x - 2, closest_y - 2], [4, 4])
        debugShapes[ellipse.id].append(point_debug)

    # first test if the bounding box of the ellipse intersects the rectangle for optimization
    if (rect_x > ell_x + ell_w / 2 or
        rect_x + rect_w < ell_x - ell_w / 2 or
        rect_y > ell_y + ell_h / 2 or
        rect_y + rect_h < ell_y - ell_h / 2):
        # Core.log_message("Bounding box check failed in rect2ellipseCollision", True)
        return False

    # Find the closest point on the rectangle to the ellipse center
    closest_x = max(rect_x, min(ell_x, rect_x + rect_w))
    closest_y = min(rect_y + rect_h, max(ell_y, rect_y))

    # Normalize the distance by the ellipse radii
    dx = (ell_x - closest_x) / (ell_w / 2)
    dy = (ell_y - closest_y) / (ell_h / 2)

    # If the normalized distance is <= 1, they collide
    return dx * dx + dy * dy <= 1

def rect2rectCollision(rect1: 'Core.object', rect2: 'Core.object') -> bool:
    # Rectangle: position = [x, y] (top-left), size = [width, height]
    r1_x, r1_y = rect1.position
    r1_w, r1_h = rect1.size
    r2_x, r2_y = rect2.position
    r2_w, r2_h = rect2.size

    global shouldDebugCollisions, debugShapes
    if(shouldDebugCollisions):
        # draw the edges of rect 1
        if rect1.id not in debugShapes:
            debugShapes[rect1.id] = []
            rect1_debug = Core.object(rect1.core, shapes.RECTANGLE, (255, 0, 0), [r1_x, r1_y], [r1_w, r1_h])
            rect1_debug.color = (255, 0, 0, 128)
            debugShapes[rect1.id].append(rect1_debug)

        if rect2.id not in debugShapes:
            debugShapes[rect2.id] = []
            rect2_debug = Core.object(rect2.core, shapes.RECTANGLE, (0, 255, 0), [r2_x, r2_y], [r2_w, r2_h])
            rect2_debug.color = (0, 255, 0, 128)
            debugShapes[rect2.id].append(rect2_debug)

    # Check for collision
    return (r1_x < r2_x + r2_w and
            r1_x + r1_w > r2_x and
            r1_y < r2_y + r2_h and
            r1_y + r1_h > r2_y)

def ellipse2ellipseCollision(ell1: 'Core.object', ell2: 'Core.object') -> bool:
    # Ellipse: position = [cx, cy] (center), size = [width, height] (diameters)
    e1_x, e1_y = ell1.position
    e1_w, e1_h = ell1.size
    e2_x, e2_y = ell2.position
    e2_w, e2_h = ell2.size
    
    # Calculate distance between centers
    dx = e1_x - e2_x
    dy = e1_y - e2_y
    
    # Normalize by the sum of radii
    # This is a simplified approach for ellipse collision
    normalized_x = dx / ((e1_w + e2_w) / 2)
    normalized_y = dy / ((e1_h + e2_h) / 2)
    
    # If the normalized distance is <= 1, they collide
    return normalized_x * normalized_x + normalized_y * normalized_y <= 1

def earlyInternalUpdate(self):
    # Perform any early internal updates here
    pass

tracked_object: 'Core.object' = None
tracking_type: TRACK_TYPE = TRACK_TYPE.SNAP
cameraSectionPosition = (0, 0)
def lateInternalUpdate(self):
    global tracked_object, cameraSectionPosition, tracking_type
    if tracked_object is not None:
        if tracking_type == TRACK_TYPE.SNAP:
            cameraSectionPosition = (math.floor(tracked_object.position[0] / self.screenSize[0]), math.floor(tracked_object.position[1] / self.screenSize[1]))
            #print("tracked object has position: ", tracked_object.position, " and cameraSectionPosition: ", cameraSectionPosition, " with screenSize: ", self.screenSize)
        elif tracking_type == TRACK_TYPE.SMOOTH:
            cameraSectionPosition = (tracked_object.position[0] / self.screenSize[0], tracked_object.position[1] / self.screenSize[1])
            # Smooth tracking logic here
    pass

last_message = ""
last_message_count = 1
last_message_lines = 1  # Track how many lines the last message used

def _load_image(path: str) -> pygame.Surface:
    try:
        surface = pygame.image.load(path)
        return surface.convert_alpha()  # Enable alpha blending for better performance
    except FileNotFoundError:
        Core.log_message("Error loading background, couldn't find: " + path, True)
        return _load_image(os.path.join(os.path.dirname(__file__), 'internal_sprites', f"missing_texture.png"))

last_loaded_background_info = None
last_loaded_background: pygame.Surface | None = None

debugShapes: dict[str, List['Core.object']] = {}
def debugDraw(screen):
    global debugShapes, shouldDebugCollisions
    if(shouldDebugCollisions):
        for obj_list in debugShapes.values():
            for obj in obj_list:
                obj.draw(screen)

    debugShapes = {}

class Core:
    def __init__(self, sectionPixelSize=(30, 20), screen_size_multiplier=1, title="Game"):
        pygame.init()
        self.sectionPixelSize = sectionPixelSize
        self.screenSize = (sectionPixelSize[0] * screen_size_multiplier, sectionPixelSize[1] * screen_size_multiplier)
        self.screen = pygame.display.set_mode(self.screenSize)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True

        # Initialize sub-pixel offset for smooth background movement
        self._sub_pixel_offset_x = 0.0
        self._sub_pixel_offset_y = 0.0

        # expose pygame.xxx classes
        self.draw = pygame.draw
        self.image = pygame.image
        self.font = pygame.font

        # first check how many level_x files exist, then call the createBackgrounds method on each image
        continueSearchingLevelImages = True
        currentLevel = 0
        while continueSearchingLevelImages:
            if os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'levels', f'level_{currentLevel}.png')):
                final_path = os.path.join(os.path.dirname(__file__), '..', 'levels', f'level_{currentLevel}.png')
                self.chunkCount = BackgroundCreator().createBackgrounds(final_path, currentLevel, sectionPixelSize)
                currentLevel += 1
            else:
                continueSearchingLevelImages = False

        self.tickrate = 60

    def run(self, update, mouse_clicked, draw, drawBackground, drawForeground, drawUI, GameLoad):
        GameLoad()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if hasattr(self, '_Core__buttons'):
                        for button in self._Core__buttons:
                            if(button._button__position_within_bounds(event.pos)):
                                button._button__button_pressed(button)
                            else:
                                self.log_message("button was not clicked!")
                    else:
                        self.log_message("no __buttons attribute")
                    mouse_clicked(event.pos)

            self.keys = pygame.key.get_pressed()
            earlyInternalUpdate(self)
            update()
            lateInternalUpdate(self)

            global cameraSectionPosition
            #print("calling drawBackground with cameraSectionPosition: ", cameraSectionPosition)
            drawBackground(self.screen, cameraSectionPosition)
            draw(self.screen)
            
            debugDraw(self.screen)

            drawForeground(self.screen)
            drawUI(self.screen)

            pygame.display.flip()
            self.clock.tick(self.tickrate)

        pygame.quit()

    def isKeyPressed(self, key_name: str) -> bool:

        if(key_name.lower() == "ctrl" or key_name.lower() == "shift" or key_name.lower() == "alt" or key_name.lower() == "meta" or key_name.lower() == "super"):
            key_name = "L" + key_name

        if(len(key_name) > 1):
            key_name_final = key_name.upper()
        else:
            key_name_final = key_name.lower()

        try:
            key_code = getattr(pygame, f"K_{key_name_final}")
        except AttributeError:
            raise ValueError(f"Invalid key name: {key_name} (result: {"K_"+key_name_final})")
        return self.keys[key_code]

    def loadBackground(self, level: int, coordinates: list[int] | tuple[int, int] | list[float] | tuple[float, float]):
        # if tracking is in snap mode, simply display the background accosiated with the position
        if tracking_type == TRACK_TYPE.SNAP:
            background_path = os.path.join(os.path.dirname(__file__), 'backgrounds', f"{level}_{coordinates[0]}_{coordinates[1]}.png")
            return pygame.transform.scale(_load_image(background_path), pygame.display.get_surface().get_size())
        #if its smooth get the 1-4 backgrounds the camera will cover
        elif tracking_type == TRACK_TYPE.SMOOTH:
            #Core.log_message("loading background tiles for smooth tracking")

            # Calculate which tiles we need based on camera position
            # Get the base tile coordinates (floor of the camera position)
            base_x = math.floor(coordinates[0])
            base_y = math.floor(coordinates[1])

            global last_loaded_background_info, last_loaded_background
            if(last_loaded_background_info == (base_x, base_y)):
                #Core.log_message("Reusing last loaded background")
                return last_loaded_background
            last_loaded_background_info = (base_x, base_y)

            # Create a surface that's 2x2 tiles in size
            tile_width = self.sectionPixelSize[0]
            tile_height = self.sectionPixelSize[1]
            combined_surface = pygame.Surface((tile_width * 3, tile_height * 3))
            combined_surface = combined_surface.convert_alpha()  # Enable alpha blending
            
            # Load and blit the 4 tiles around the camera position
            tile_positions = [
                (base_x, base_y),       # middle-middle
                (base_x + 1, base_y),   # middle-right
                (base_x, base_y + 1),   # Bottom-middle
                (base_x + 1, base_y + 1), # Bottom-right
                (base_x - 1, base_y + 1), # bottom-left
                (base_x - 1, base_y), # middle-left
                (base_x, base_y - 1), # top-middle
                (base_x - 1, base_y - 1), # top-left
                (base_x + 1, base_y - 1) # top-right
            ]
            
            blit_positions = [
                (tile_width, tile_height),       # middle-middle (center)
                (tile_width * 2, tile_height),   # middle-right
                (tile_width, tile_height * 2),   # Bottom-middle
                (tile_width * 2, tile_height * 2), # Bottom-right
                (0, tile_height * 2),            # bottom-left
                (0, tile_height),                # middle-left
                (tile_width, 0),                 # top-middle
                (0, 0),                          # top-left
                (tile_width * 2, 0)              # top-right
            ]
            
            for i, (tile_x, tile_y) in enumerate(tile_positions):
                tile_path = os.path.join(os.path.dirname(__file__), 'backgrounds', f"{level}_{tile_x}_{tile_y}.png")
                tile_surface = _load_image(tile_path)
                
                # Scale the tile to the section size if needed
                if tile_surface.get_size() != (tile_width, tile_height):
                    tile_surface = pygame.transform.scale(tile_surface, (tile_width, tile_height))
                
                combined_surface.blit(tile_surface, blit_positions[i])
            
            # Scale the combined surface to screen size
            scale_mult_x = self.screenSize[0] / self.sectionPixelSize[0]
            scale_mult_y = self.screenSize[1] / self.sectionPixelSize[1]
            
            # Save for debugging
            #pygame.image.save(combined_surface, os.path.join(os.path.dirname(__file__), '..', f"background_{level}_combined.png"))
            last_loaded_background = pygame.transform.scale(combined_surface, (self.screenSize[0] * 3, self.screenSize[1] * 3))
            return last_loaded_background

    def drawBackground(self, background):
        if background is not None:
            global cameraSectionPosition, tracking_type
            
            if tracking_type == TRACK_TYPE.SMOOTH:
                # For smooth tracking with 2x2 tile system
                # Calculate the fractional offset within the current tile
                fractional_x = cameraSectionPosition[0] - math.floor(cameraSectionPosition[0])
                fractional_y = cameraSectionPosition[1] - math.floor(cameraSectionPosition[1])
                
                # Calculate the offset in screen pixels
                # Since the background is 2x the screen size, we need to position it correctly
                scale_mult_x = self.screenSize[0] / self.sectionPixelSize[0]
                scale_mult_y = self.screenSize[1] / self.sectionPixelSize[1]
                
                # The offset determines how much of the 2x2 surface we show
                # When fractional position is 0,0 we show the top-left tile
                # When fractional position is 1,1 we show the bottom-right tile
                offset_x = -fractional_x * self.screenSize[0]# - self.screenSize[0]
                offset_y = -fractional_y * self.screenSize[1]# - self.screenSize[1]

                #Core.log_message(f"drawing background at offset: ({offset_x}, {offset_y}) with fractional position: ({fractional_x}, {fractional_y})")

                #pygame.image.save(background, os.path.join(os.path.dirname(__file__), '..', f"background_final.png"))

                self.screen.blit(background, (offset_x, offset_y))
            else:
                # SNAP mode or default - draw at (0, 0)
                self.screen.blit(background, (0, 0))

    def checkCollision(self, obj1: 'Core.object', obj2: 'Core.object') -> bool:
        if obj1.shape == shapes.RECTANGLE and obj2.shape == shapes.RECTANGLE:
            return rect2rectCollision(obj1, obj2)
        elif obj1.shape == shapes.ELLIPSE and obj2.shape == shapes.ELLIPSE:
            return ellipse2ellipseCollision(obj1, obj2)
        elif obj1.shape == shapes.RECTANGLE and obj2.shape == shapes.ELLIPSE:
            return rect2ellipseCollision(obj1, obj2)
        elif obj1.shape == shapes.ELLIPSE and obj2.shape == shapes.RECTANGLE:
            return rect2ellipseCollision(obj2, obj1)
        return False
    def checkCollisionWithList(self, obj1: 'Core.object', obj2: List['Core.object']) -> bool:
        for obj in obj2:
            if self.checkCollision(obj1, obj):
                return True
        return False
    def setCameraFollow(self, obj: 'Core.object', track_type: TRACK_TYPE = TRACK_TYPE.SNAP):
        global tracked_object, tracking_type
        tracked_object = obj
        tracking_type = track_type

    def drawText(self, screen, text: str, position: tuple[int, int], font_size: int = 36, color: tuple[int, int, int] = (255, 255, 255)):
        font = self.font.Font(None, font_size)
        text_surface = font.render(text, True, color)
        scaled_position = (position[0] * self.screenSize[0] - text_surface.get_size()[0] / 2, position[1] * self.screenSize[1] - text_surface.get_size()[1] / 2)
        screen.blit(text_surface, scaled_position)

    def drawImage(self, screen, image: str, position: tuple[int, int], size: tuple[int, int]):
        loaded_image = _load_image(os.path.join(os.path.dirname(__file__), '..', 'sprites', image))
        scaled_image = pygame.transform.scale(loaded_image, size)
        scaled_position = (position[0] * self.screenSize[0], position[1] * self.screenSize[1])
        screen.blit(scaled_image, scaled_position)

    @staticmethod
    def log_message(message: str, error: bool = False):
        global last_message, last_message_count, last_message_lines
        
        # Get terminal width, default to 80 if not available
        try:
            terminal_width = shutil.get_terminal_size().columns
        except:
            terminal_width = 80
        
        if last_message != message:
            last_message = message
            last_message_count = 1
            
            # Calculate how many lines this message will use
            prefix = "Error: " if error else "Message: "
            full_message = prefix + message
            last_message_lines = max(1, (len(full_message) + terminal_width - 1) // terminal_width)
            
            if error:
                print("Error:", message)
            else:
                print("Message:", message)
        else:
            # add a X [times] to the end of the message
            last_message_count += 1
            
            # Clear all lines that the previous message used
            for _ in range(last_message_lines):
                print('\033[A\033[K', end='')
            
            # Calculate how many lines the new message will use
            prefix = "Error: " if error else "Message: "
            full_message = f"{prefix}{last_message} [x{last_message_count}]"
            last_message_lines = max(1, (len(full_message) + terminal_width - 1) // terminal_width)
            
            # print the error message with the count
            if(error):
                print(f"Error: {last_message} [x{last_message_count}]")
            else:
                print(f"Message: {last_message} [x{last_message_count}]")

    def debugCollisions(self, shouldDebug: bool):
        global shouldDebugCollisions
        shouldDebugCollisions = shouldDebug

    def setTickrate(self, tps: int | None):
        if(tps is None or tps <= 0):
            self.tickrate = 60
        else:
            self.tickrate = tps

    class object:
        def __init__(self, core: 'Core', shape: 'shapes', color: list[int] | tuple[int, int, int] | tuple[int, int, int, int], position: list[float], size: list[float] | tuple[float, float], image: str | None = None):
            self.core = core
            self.shape = shape
            self.color = color.copy() if hasattr(color, 'copy') else color  # For tuples which don't have copy()
            self.position = position.copy()
            self.original_position = position.copy()
            self.size = size.copy() if hasattr(size, 'copy') else size  # For tuples which don't have copy()
            self.image = image

            self.move_restrictions = (None, None)

            # random hash
            self.id = str(uuid.uuid4())

        def draw(self, screen):
            global cameraSectionPosition, tracking_type
            adjusted_position = (self.position[0] - (cameraSectionPosition[0] * self.core.screenSize[0]), self.position[1] - (cameraSectionPosition[1] * self.core.screenSize[1]))

            if(tracking_type == TRACK_TYPE.SMOOTH):
                adjusted_position = (adjusted_position[0] + self.core.screenSize[0] / 2, adjusted_position[1] + self.core.screenSize[1] / 2)
            
            # optimize object draw culling
            if self.shape == shapes.RECTANGLE:
                if adjusted_position[0] + self.size[0] < 0 or adjusted_position[0] > self.core.screenSize[0] or adjusted_position[1] + self.size[1] < 0 or adjusted_position[1] > self.core.screenSize[1]:
                    return
            elif self.shape == shapes.ELLIPSE:
                if adjusted_position[0] + self.size[0]/2 < 0 or adjusted_position[0] - self.size[0]/2 > self.core.screenSize[0] or adjusted_position[1] + self.size[1]/2 < 0 or adjusted_position[1] - self.size[1]/2 > self.core.screenSize[1]:
                    return
            elif self.shape == shapes.IMAGE:
                if adjusted_position[0] + self.size[0] < 0 or adjusted_position[0] > self.core.screenSize[0] or adjusted_position[1] + self.size[1] < 0 or adjusted_position[1] > self.core.screenSize[1]:
                    return

            # Core.log_message("drawing object at adjusted position: " + str(adjusted_position) + " with cameraSectionPosition: " + str(cameraSectionPosition) + " and original position: " + str(self.position) + " and screen size: " + str(self.core.screenSize) + " and shape: " + str(self.shape) + " with intermidiate level position screen size: " + str([cameraSectionPosition[0] * self.core.screenSize[0], cameraSectionPosition[1] * self.core.screenSize[1]]))

            loaded_image = None
            if(self.image is not None and self.shape == shapes.IMAGE and os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'sprites', self.image))):
                loaded_image = _load_image(os.path.join(os.path.dirname(__file__), '..', 'sprites', self.image))

            drawShape(screen, self.shape, self.color, adjusted_position, self.size, loaded_image, self.border if hasattr(self, 'border') else None)

        def move(self, dx, dy):
            self.position[0] += dx
            if (self.move_restrictions[0] is not None):
                self.position[0] = max(self.move_restrictions[0][0], min(self.position[0], self.move_restrictions[0][1]))

            self.position[1] += dy
            if (self.move_restrictions[1] is not None):
                self.position[1] = max(self.move_restrictions[1][0], min(self.position[1], self.move_restrictions[1][1]))

        def moveAndCollide(self, dx, dy, obstacles: List['Core.object']):
            original_pos = self.position.copy()
            self.move(dx, dy)

            # Check if the full movement causes a collision
            if self.core.checkCollisionWithList(self, obstacles):
                self.position = original_pos.copy()  # Reset to start
                
                # Try sliding along each axis separately with binary search
                # First try moving only horizontally
                if dx != 0:
                    stepX = dx
                    for _ in range(10):  # Binary search for X movement
                        stepX = stepX / 2
                        self.move(stepX, 0)
                        if self.core.checkCollisionWithList(self, obstacles):
                            self.move(-stepX, 0)  # Back out this step
                
                # Then try moving only vertically
                if dy != 0:
                    stepY = dy
                    for _ in range(10):  # Binary search for Y movement
                        stepY = stepY / 2
                        self.move(0, stepY)
                        if self.core.checkCollisionWithList(self, obstacles):
                            self.move(0, -stepY)  # Back out this step

        def set_position(self, x, y):
            self.position = [x - (self.size[0] / 2), y - (self.size[1] / 2)]

        def reset_position(self, x: bool = True, y: bool = True):
            if x:
                self.position[0] = self.original_position[0]
            if y:
                self.position[1] = self.original_position[1]

        def destroy(self):
            del self

        def get_rect(self) -> pygame.Rect:
            return pygame.Rect(self.position[0], self.position[1], self.size[0], self.size[1])

        def set_move_restriction(self, restrict_x: tuple[float, float] | None, restrict_y: tuple[float, float] | None):
            self.move_restrictions = (restrict_x, restrict_y)

    class uiObject:
        class button:
            def __init__(self, core: 'Core', position: tuple[float, float], size: tuple[float, float], color: tuple[int, int, int], textColor: tuple[int, int, int], text: str, button_pressed):
                self.__core = core
                if not hasattr(self.__core, '_Core__buttons'):
                    self.__core._Core__buttons = []
                self.__core._Core__buttons.append(self)
                self.__button_pressed = button_pressed
                self.position = position
                self.size = size
                self.color = color
                self.textColor = textColor
                self.text = text
            
            def __calculate_font_size(self):
                """Calculate font size to fill button height minus 2 pixels padding on each side"""
                target_height = self.size[1] - 4  # minus 2 pixels on each side
                
                # Direct conversion from pixels to font size
                # Pygame fonts typically have a height that's about 0.8-0.9 times the font size
                # We'll use 0.85 as a good middle ground
                estimated_font_size = int(target_height * 1.8)

                # Clamp to reasonable bounds
                font_size = max(6, min(estimated_font_size, 500))
                
                return font_size
            
            def __position_within_bounds(self, pos: tuple[float, float]):
                if(pos[0] > self.position[0] - self.size[0] / 2 and pos[0] < self.position[0] + self.size[0] / 2 and
                   pos[1] > self.position[1] - self.size[1] / 2 and pos[1] < self.position[1] + self.size[1] / 2):
                    return True
                return False

            def draw(self, screen):
                drawShape(screen, shapes.RECTANGLE, self.color, [self.position[0] - self.size[0] / 2, self.position[1] - self.size[1] / 2], self.size, None, None)
                font_size = self.__calculate_font_size()
                self.__core.drawText(screen, self.text, (self.position[0] / self.__core.screenSize[0], self.position[1] / self.__core.screenSize[1]), font_size, self.textColor)

            def unload(self):
                self.__core = None
                self.__button_pressed = None
                self.position = None
                self.size = None
                self.color = None
                self.textColor = None
                self.text = None