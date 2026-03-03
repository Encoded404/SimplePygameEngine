from __future__ import annotations

import os
from queue import Queue
import pygame
import math
from typing import List
import shutil
import uuid
import traceback
from types import SimpleNamespace

from enum import Enum
from .createBackgrounds import BackgroundCreator


class Vector2:
    """Lightweight 2D vector for positions, offsets, and movement."""

    __slots__ = ("x", "y")

    def __init__(self, x: float | list[float] | tuple[float, float] | Vector2 = 0.0, y: float | None = None):
        if y is None and isinstance(x, (Vector2, list, tuple)):
            self.x, self.y = self._extract_components(x)
        else:
            self.x = float(x)
            self.y = float(x if y is None else y)

    @staticmethod
    def _extract_components(value: Vector2 | list[float] | tuple[float, float] | float | int) -> tuple[float, float]:
        if isinstance(value, Vector2):
            return value.x, value.y
        if isinstance(value, (list, tuple)):
            if len(value) < 2:
                raise ValueError("Vector2 needs at least two values")
            return float(value[0]), float(value[1])
        if isinstance(value, (int, float)):
            scalar = float(value)
            return scalar, scalar
        raise TypeError("Cannot extract Vector2 components from value: {}".format(value))

    def copy(self) -> Vector2:
        return Vector2(self.x, self.y)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def to_list(self) -> list[float]:
        return [self.x, self.y]

    @property
    def length(self) -> float:
        return math.hypot(self.x, self.y)

    @property
    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vector2:
        mag = self.length
        if mag == 0:
            return Vector2(0.0, 0.0)
        return Vector2(self.x / mag, self.y / mag)

    def distance_to(self, value: Vector2 | list[float] | tuple[float, float]) -> float:
        ox, oy = self._extract_components(value)
        return math.hypot(self.x - ox, self.y - oy)

    def dot(self, vector: Vector2 | list[float] | tuple[float, float]) -> float:
        ox, oy = self._extract_components(vector)
        return self.x * ox + self.y * oy

    def __getitem__(self, index: int) -> float:
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        raise IndexError("Vector2 index out of range")

    def __setitem__(self, index: int, value: float) -> None:
        if index == 0:
            self.x = float(value)
            return
        if index == 1:
            self.y = float(value)
            return
        raise IndexError("Vector2 index out of range")

    def __iter__(self):
        yield self.x
        yield self.y

    def __len__(self) -> int:
        return 2

    def __eq__(self, other) -> bool:
        if not isinstance(other, (Vector2, list, tuple)):
            return False
        
        try:
            ox, oy = self._extract_components(other)
        except (TypeError, ValueError):
            return False
        
        return self.x == ox and self.y == oy

    def __repr__(self) -> str:
        return f"({self.x}, {self.y})"

    def __add__(self, other):
        if not isinstance(other, (Vector2, list, tuple)):
            return NotImplemented
        ox, oy = self._extract_components(other)
        return Vector2(self.x + ox, self.y + oy)

    def __sub__(self, other):
        if not isinstance(other, (Vector2, list, tuple)):
            return NotImplemented
        ox, oy = self._extract_components(other)
        return Vector2(self.x - ox, self.y - oy)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __mul__(self, scalar: float) -> Vector2:
        if not isinstance(scalar, (int, float)):
            raise TypeError("Vector2 multiplication requires a scalar")
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide Vector2 by zero")
        return Vector2(self.x / scalar, self.y / scalar)

class shapes(Enum):
    RECTANGLE = 1
    ELLIPSE = 2
    IMAGE = 3
    CUSTOM = 4

class TRACK_TYPE(Enum):
    SNAP = 1
    SMOOTH = 2

shouldDebugCollisions = False
_MISSING = object()

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
        # list of all created objects (registered in Core.object.__init__)
        self._objects: list[Core.object] = []
        # shared state dictionary available to scripts
        self.shared_state: dict = {}

    def run(self, update, mouse_clicked, draw, drawBackground, drawForeground, drawUI, GameLoad):
        # Allow any of the callbacks to be None or non-callable. Guard calls accordingly.
        if callable(GameLoad):
            try:
                GameLoad()
            except Exception as e:
                self.log_message(f"GameLoad raised exception: {e}", True)

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
                        pass
                        # this means the game has not registered any buttons yet
                        #self.log_message("no __buttons attribute")
                    if callable(mouse_clicked):
                        try:
                            mouse_clicked(event.pos)
                        except Exception as e:
                            self.log_message(f"mouse_clicked raised exception: {e}", True)

            self.keys = pygame.key.get_pressed()
            earlyInternalUpdate(self)
            if callable(update):
                try:
                    update()
                except Exception as e:
                    self.log_message(f"update raised exception: {e}", True)
            lateInternalUpdate(self)

            # Run per-object script updates (iterate over a snapshot to avoid modification during loop)
            try:
                for obj in list(Core._get_attr(self, '_objects', [])):
                    for script in Core._get_attr(obj, 'scripts', []):
                        if hasattr(script, 'update') and callable(script.update):
                            try:
                                script.update(obj)
                            except Exception as e:
                                Core._log_script_exception(script, 'script.update', e)
            except Exception as e:
                self.log_message(f"object script update loop failed: {e}", True)

            global cameraSectionPosition
            # Call rendering callbacks only if provided
            if callable(drawBackground):
                try:
                    drawBackground(self.screen, cameraSectionPosition)
                except Exception as e:
                    self.log_message(f"drawBackground raised exception: {e}", True)

            if callable(draw):
                try:
                    draw(self.screen)
                except Exception as e:
                    self.log_message(f"draw raised exception: {e}", True)

            debugDraw(self.screen)

            if callable(drawForeground):
                try:
                    drawForeground(self.screen)
                except Exception as e:
                    self.log_message(f"drawForeground raised exception: {e}", True)

            if callable(drawUI):
                try:
                    drawUI(self.screen)
                except Exception as e:
                    self.log_message(f"drawUI raised exception: {e}", True)

            pygame.display.flip()
            self.clock.tick(self.tickrate)

        pygame.quit()

    def stop(self):
        self.running = False

    def isKeyPressed(self, key_name: str) -> bool:

        if(key_name.lower() == "ctrl" or key_name.lower() == "shift" or key_name.lower() == "alt" or key_name.lower() == "meta" or key_name.lower() == "super"):
            key_name = "L" + key_name

        if(len(key_name) > 1):
            key_name_final = key_name.upper()
        else:
            key_name_final = key_name.lower()

        try:
            key_code = Core._get_attr(pygame, f"K_{key_name_final}")
        except AttributeError:
            raise ValueError(f"Invalid key name: {key_name} (result: {"K_"+key_name_final})")
        return self.keys[key_code]

    def loadBackground(self, level: int, coordinates: list[int] | tuple[int, int] | list[float] | tuple[float, float] | Vector2):
        # if tracking is in snap mode, simply display the background accosiated with the position
        coords = coordinates if isinstance(coordinates, Vector2) else Vector2(coordinates if isinstance(coordinates, (list, tuple)) else coordinates)
        snap_coord = (int(coords.x), int(coords.y))
        if tracking_type == TRACK_TYPE.SNAP:
            background_path = os.path.join(os.path.dirname(__file__), 'backgrounds', f"{level}_{snap_coord[0]}_{snap_coord[1]}.png")
            return pygame.transform.scale(_load_image(background_path), pygame.display.get_surface().get_size())
        #if its smooth get the 1-4 backgrounds the camera will cover
        elif tracking_type == TRACK_TYPE.SMOOTH:
            #Core.log_message("loading background tiles for smooth tracking")

            # Calculate which tiles we need based on camera position
            # Get the base tile coordinates (floor of the camera position)
            base_x = math.floor(coords.x)
            base_y = math.floor(coords.y)

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
        proxies1 = Core._build_collision_proxies(obj1)
        proxies2 = Core._build_collision_proxies(obj2)

        for proxy1 in proxies1:
            for proxy2 in proxies2:
                if proxy1.shape == shapes.RECTANGLE and proxy2.shape == shapes.RECTANGLE:
                    if rect2rectCollision(proxy1, proxy2):
                        return True
                elif proxy1.shape == shapes.ELLIPSE and proxy2.shape == shapes.ELLIPSE:
                    if ellipse2ellipseCollision(proxy1, proxy2):
                        return True
                elif proxy1.shape == shapes.RECTANGLE and proxy2.shape == shapes.ELLIPSE:
                    if rect2ellipseCollision(proxy1, proxy2):
                        return True
                elif proxy1.shape == shapes.ELLIPSE and proxy2.shape == shapes.RECTANGLE:
                    if rect2ellipseCollision(proxy2, proxy1):
                        return True
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

    @staticmethod
    def has_function(source, name) -> bool:
        return Core._has_attr(source = source, attr_name = name, require_callable = True)
    
    @staticmethod
    def has_variable(source, name) -> bool:
        return Core._has_attr(source = source, attr_name = name, require_callable = False)

    @staticmethod
    def normalize(vector: Vector2 | list[float] | tuple[float, float]) -> Vector2:
        if isinstance(vector, Vector2):
            x, y = vector.x, vector.y
        else:
            x, y = vector
        length = math.hypot(x, y)
        if length == 0:
            return Vector2(0.0, 0.0)
        return Vector2(x / length, y / length)
    
    @staticmethod
    def _has_attr(source, attr_name, *, require_callable: bool | None = None) -> bool:
        if not hasattr(source, attr_name):
            return False
        value = getattr(source, attr_name)
        if require_callable is True:
            return callable(value)
        if require_callable is False:
            return not callable(value)
        return True

    @staticmethod
    def _get_attr(source, attr_name, default=_MISSING):
        if default is _MISSING:
            return getattr(source, attr_name)
        return getattr(source, attr_name, default)

    @staticmethod
    def _script_name(script):
        if script is None:
            return "<unknown>"
        return getattr(script, '__qualname__', getattr(script, '__name__', getattr(script, '__class__', type(script)).__name__))

    @staticmethod
    def _log_script_exception(script, context: str, exc: Exception):
        name = Core._script_name(script)
        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        Core.log_message(f"{context} ({name}) raised:\n{tb}", True)

    @staticmethod
    def _get_custom_colliders(obj):
        colliders = []
        for script in Core._get_attr(obj, 'scripts', []):
            if not Core.has_function(script, 'getColliders'):
                continue
            try:
                result = script.getColliders(obj)
            except Exception as e:
                Core._log_script_exception(script, 'script.getColliders', e)
                continue
            if not result:
                continue
            if isinstance(result, (list, tuple)):
                colliders.extend(result)
            else:
                colliders.append(result)
        return colliders

    @staticmethod
    def _normalize_collider_info(obj, info):
        if isinstance(info, dict):
            shape = info.get('shape', obj.shape)
            offset = tuple(info.get('offset', (0, 0)))
            size = info.get('size', obj.size)
        else:
            shape = getattr(info, 'shape', obj.shape)
            offset = tuple(getattr(info, 'offset', (0, 0)))
            size = getattr(info, 'size', obj.size)

        size_value = None
        if isinstance(size, (list, tuple)) and len(size) == 2:
            size_value = [size[0], size[1]]
        elif hasattr(size, 'copy'):
            size_value = size.copy()
        else:
            size_value = [size, size]

        return shape, offset, size_value

    @staticmethod
    def _build_collision_proxies(obj):
        colliders = Core._get_custom_colliders(obj)
        proxies = []
        if not colliders:
            proxies.append(SimpleNamespace(
                shape=obj.shape,
                position=obj.position.copy(),
                size=obj.size.copy() if hasattr(obj.size, 'copy') else list(obj.size),
                core=obj.core,
                id=obj.id,
            ))
            return proxies

        for idx, collider in enumerate(colliders):
            shape, offset, size = Core._normalize_collider_info(obj, collider)
            proxies.append(SimpleNamespace(
                shape=shape,
                position=[obj.position[0] + offset[0], obj.position[1] + offset[1]],
                size=size,
                core=obj.core,
                id=f"{obj.id}:{idx}",
            ))
        return proxies

    def debugCollisions(self, shouldDebug: bool):
        global shouldDebugCollisions
        shouldDebugCollisions = shouldDebug

    def setTickrate(self, tps: int | None):
        if(tps is None or tps <= 0):
            self.tickrate = 60
        else:
            self.tickrate = tps

    def clean_object_list(self, objects: list['Core.object']):
        """Keep only objects that are still registered with this Core."""

        if not objects:
            return
        active_objects = set(self._objects)
        objects[:] = [obj for obj in objects if hasattr(obj, "core") and obj in active_objects]

    class object:
        def __init__(self, core: 'Core', shape: 'shapes', color: list[int] | tuple[int, int, int] | tuple[int, int, int, int], position: Vector2 | list[float] | tuple[float, float], size: list[float] | tuple[float, float], image: str | None = None, scripts: list | None = None, arguments: dict | None = None):
            self.core = core
            self.shape = shape
            self.color = color.copy() if hasattr(color, 'copy') else color  # For tuples which don't have copy()
            normalized_position = Vector2(position)
            self.position = normalized_position.copy()
            self.original_position = normalized_position.copy()
            self.size = size.copy() if hasattr(size, 'copy') else size  # For tuples which don't have copy()
            self.image = image
            self.arguments = arguments.copy() if arguments else {}

            # script instances attached to this object; each script may implement ready(obj), update(obj), draw(screen, obj)
            self.scripts: list = []

            # register object with core
            try:
                if not hasattr(self.core, '_objects'):
                    self.core._objects = []
                self.core._objects.append(self)
            except Exception:
                pass

            # if initial scripts provided, attach them
            if scripts:
                for s in scripts:
                    self.attach_script(s)

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
            # If this object uses CUSTOM shape, let attached scripts perform drawing
            if self.shape == shapes.CUSTOM:
                drew = False
                for script in Core._get_attr(self, 'scripts', []):
                    if hasattr(script, 'draw') and callable(script.draw):
                        try:
                            script.draw(screen, self)
                            drew = True
                        except Exception as e:
                            Core._log_script_exception(script, 'script.draw', e)
                if drew:
                    return
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
            self.position = Vector2(x - (self.size[0] / 2), y - (self.size[1] / 2))

        def reset_position(self, x: bool = True, y: bool = True):
            if x:
                self.position[0] = self.original_position[0]
            if y:
                self.position[1] = self.original_position[1]

        def destroy(self):
            # unregister from core list if present
            try:
                if hasattr(self.core, '_objects') and self in self.core._objects:
                    self.core._objects.remove(self)
            except Exception:
                pass
            # clear scripts
            try:
                self.scripts.clear()
            except Exception:
                pass
            del self

        def __instantiate_script(self, script_entry):
            constructor = script_entry
            raw_args = ()
            raw_kwargs = {}
            if isinstance(script_entry, dict):
                constructor = script_entry.get('class') or script_entry.get('script') or constructor
                raw_args = script_entry.get('args', ())
                raw_kwargs = script_entry.get('kwargs', {})
            elif isinstance(script_entry, (list, tuple)):
                if len(script_entry) == 0:
                    return None
                constructor = script_entry[0]
                raw_args = script_entry[1] if len(script_entry) > 1 else ()
                raw_kwargs = script_entry[2] if len(script_entry) > 2 else {}

            if isinstance(raw_args, dict):
                raw_kwargs = raw_args
                raw_args = ()

            if isinstance(raw_args, (list, tuple)):
                args = tuple(raw_args)
            elif raw_args is None:
                args = ()
            else:
                args = (raw_args,)

            kwargs = dict(raw_kwargs) if isinstance(raw_kwargs, dict) else {}

            if callable(constructor):
                try:
                    return constructor(*args, **kwargs)
                except TypeError:
                    return constructor
            return constructor

        def attach_script(self, script):
            """Attach a script object to this object. Script may implement ready(obj), update(obj), draw(screen, obj)."""
            if not hasattr(self, 'scripts'):
                self.scripts = []
            instance = script
            if script is not None:
                instance = self.__instantiate_script(script)
            if instance is None:
                return
            try:
                setattr(instance, 'object', self)
                setattr(instance, 'core', self.core)
            except Exception:
                pass
            self.scripts.append(instance)
            # call ready lifecycle method if present
            if hasattr(instance, 'ready') and callable(instance.ready):
                try:
                    instance.ready(self)
                except Exception as e:
                    Core._log_script_exception(instance, 'script.ready', e)

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