from engine.core import Core, shapes, TRACK_TYPE

# settings
player_speed = 5
player_size = 50

starting_health = 5
# a multiplier for the screen size of the window
screen_size = 15
# the pixel count of each section, make sure the image dimensions are multiples of this
section_size = (60, 40)
# end of settings

bounds = (section_size[0] * screen_size, section_size[1] * screen_size)

core = Core(section_size, screen_size, "game title")

# get middle of screen
starting_player_pos = [(bounds[0]) / 2 - (player_size / 2), (bounds[1]) / 2 - (player_size / 2)]

Core.log_message(f"starting player pos: {starting_player_pos}")

player_obj = core.object(core, shapes.RECTANGLE, (0, 255, 0), starting_player_pos, [player_size,player_size])

death_list = [
    core.object(core, shapes.RECTANGLE, (255, 0, 0), [100, 100], [50, 50])
]
obstacle_color = (50, 50, 50)
obstacle_list = [
    core.object(core, shapes.RECTANGLE, obstacle_color, [250, 200], [200, 50]),
    core.object(core, shapes.ELLIPSE, obstacle_color, [475, 200], [50, 50]),
    core.object(core, shapes.IMAGE, (255, 0, 0), [600, 300], [50, 50], "swirl.png")
]

current_level = 0
level_pos = [0, 0]
last_level_info = [0, 0, 0]
current_background = None

current_health = starting_health

def update():
    global starting_player_pos, player_obj, level_pos, current_background, section_size, current_health

    speed_multiplier = 1
    if core.isKeyPressed("shift"):
        speed_multiplier = 3
    
    # game logic here
    
    move_amount = [0, 0]
    final_move_speed = player_speed * speed_multiplier
    if core.isKeyPressed("w"):
        move_amount[1] -= final_move_speed
    if core.isKeyPressed("s"):
        move_amount[1] += final_move_speed
    if core.isKeyPressed("a"):
        move_amount[0] -= final_move_speed
    if core.isKeyPressed("d"):
        move_amount[0] += final_move_speed
    
    if(core.isKeyPressed("r")):
        player_obj.reset_position()
        global starting_health
        current_health = starting_health

    if(core.isKeyPressed("t")):
        core.image.save(current_background, "screenshot.png")

    
    player_obj.moveAndCollide(move_amount[0], move_amount[1], obstacle_list)

    if core.checkCollisionWithList(player_obj, death_list):
        #global current_health
        Core.log_message("collision detected")

        player_obj.reset_position()
        current_health -= 1
        if current_health <= 0:
            Core.log_message("Game Over")
            core.running = False
    pass

def mouse_clicked(position):
    pass

def GameLoad():
    global track_type, current_background, level_pos

    # set this to SMOOTH to make the camera follow smoothly, or SNAP to make it snap to sections
    track_type = TRACK_TYPE.SNAP
    core.setCameraFollow(player_obj, track_type)

    if track_type == TRACK_TYPE.SMOOTH:
        level_pos = [0.5, 0.5]

    Core.log_message("GameLoad called")

    current_background = core.loadBackground(current_level, level_pos)
    pass

def drawBackground(screen, MapPosition: tuple[int, int]):
    global level_pos, current_background, current_level, last_level_info, track_type
    level_pos = MapPosition
    screen.fill((30, 30, 30))

    if(track_type == TRACK_TYPE.SNAP):
        if (current_level != last_level_info[0] or level_pos != last_level_info[1:]):
            current_background = core.loadBackground(current_level, level_pos)
            last_level_info = (current_level, *level_pos)

    elif(track_type == TRACK_TYPE.SMOOTH):
        if(current_level != last_level_info[0] or level_pos != last_level_info[1:]):
            current_background = core.loadBackground(current_level, level_pos)
            last_level_info[0] = current_level

    if(current_background != None):
        core.drawBackground(current_background)
        pass
    else:
        Core.log_message("cant draw background. current_background was none", True)

def draw(screen):
    for death in death_list:
        death.draw(screen)
    for obstacle in obstacle_list:
        obstacle.draw(screen)

    # draw player
    player_obj.draw(screen)

def drawForeground(screen):
    pass

def drawUI(screen):
    global current_health
    health_text = f"{current_health}"
    core.drawText(screen, health_text, (0.525, 0.9), 60)
    core.drawImage(screen, "heart.png", (0.45, 0.9), (50, 50))

if __name__ == "__main__":
    core.run(update, mouse_clicked, draw, drawBackground, drawForeground, drawUI, GameLoad)