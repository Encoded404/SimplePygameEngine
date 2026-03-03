from engine.core import Core, shapes, Vector2

bounds = (900 * 2, 600 * 1.5)

core = Core(bounds, 1, "game title")

pads = [
    {
        "object": core.object(core, shapes.RECTANGLE, (255, 255, 255), Vector2(50, bounds[1] / 2 - 50), [25, 100]),
        "speed": Vector2(0, 10 * (bounds[1] / 600)),
        "controls": {
            "up": "w",
            "down": "s",
            "left": "a",
            "right": "d"
        }
    },
    {
        "object": core.object(core, shapes.RECTANGLE, (255, 255, 255), Vector2(bounds[0] - 75, bounds[1] / 2 - 50), [25, 100]),
        "speed": Vector2(0, 10 * (bounds[1] / 600)),
        "controls": {
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right"
        }
    }
]

pads[0]["object"].set_move_restriction(None, (0, bounds[1] - pads[0]["object"].size[1]))
pads[1]["object"].set_move_restriction(None, (0, bounds[1] - pads[1]["object"].size[1]))

pong = core.object(core, shapes.ELLIPSE, (255, 255, 255), Vector2(bounds[0] / 2, bounds[1] / 2), [25, 25])
pong_restrictions = ((0 + pong.size[0] / 2, bounds[0] - pong.size[0] / 2), (0 + pong.size[1] / 2, bounds[1] - pong.size[1] / 2))
pong.set_move_restriction(pong_restrictions[0], pong_restrictions[1])
pong_speed = Vector2(5 * (bounds[0] / 900), 5 * (bounds[1] / 600))

player_scores = [0, 0]
win_score = 10

# a integer representing the current stage
# 0 = title screen
# 1 = pong game
# 2 = restart screen
current_scene = 0

def update():
    global current_scene
    if(current_scene == 1):
        global pads, pong, pong_restrictions, pong_speed, win_score

        # player 1
        current_move = Vector2(0.0, 0.0)
        if core.isKeyPressed(pads[0]["controls"]["up"]):
            current_move.y -= pads[0]["speed"].y
        if core.isKeyPressed(pads[0]["controls"]["down"]):
            current_move.y += pads[0]["speed"].y
        if core.isKeyPressed(pads[0]["controls"]["left"]):
            current_move.x -= pads[0]["speed"].x
        if core.isKeyPressed(pads[0]["controls"]["right"]):
            current_move.x += pads[0]["speed"].x

        pads[0]["object"].move(current_move.x, current_move.y)

        # player 2
        current_move = Vector2(0.0, 0.0)
        if core.isKeyPressed(pads[1]["controls"]["up"]):
            current_move.y -= pads[1]["speed"].y
        if core.isKeyPressed(pads[1]["controls"]["down"]):
            current_move.y += pads[1]["speed"].y
        if core.isKeyPressed(pads[1]["controls"]["left"]):
            current_move.x -= pads[1]["speed"].x
        if core.isKeyPressed(pads[1]["controls"]["right"]):
            current_move.x += pads[1]["speed"].x

        pads[1]["object"].move(current_move.x, current_move.y)

        pong.move(pong_speed.x, pong_speed.y)

        # control game speed
        if(core.isKeyPressed("plus")):
            core.setTickrate(core.tickrate + 1)
            core.log_message(f"target tickrate: {core.tickrate}")
        if(core.isKeyPressed("minus")):
            core.setTickrate(max(1, core.tickrate - 1))
            core.log_message(f"target tickrate: {core.tickrate}")

        # bounce the pong on the edges and pads

        # left right edges: add score to the opponent and reset pong

        # hit right edge, player 1 scores
        if(pong.position[0] >= pong_restrictions[0][1]):
            player_scores[0] += 1
            if(player_scores[0] >= win_score):
                current_scene = 2
            pong_speed = Vector2(-pong_speed.x, pong_speed.y)
            pong.reset_position()
            core.log_message(f"Player 1 scored! Score: {player_scores[0]}")
        # hit left edge, player 2 scores
        if(pong.position[0] <= pong_restrictions[0][0]):
            #pong_speed = (pong_speed[0] * -1, pong_speed[1])
            player_scores[1] += 1
            if(player_scores[1] >= win_score):
                current_scene = 2
            pong_speed = Vector2(-pong_speed.x, pong_speed.y)
            pong.reset_position()
            core.log_message(f"Player 2 scored! Score: {player_scores[1]}")

        if(pong.position[1] >= pong_restrictions[1][1] or pong.position[1] <= pong_restrictions[1][0]):
            pong_speed = Vector2(pong_speed.x, -pong_speed.y)

        # hit left pad: go right
        if(core.checkCollision(pong, pads[0]["object"])):
            pong_speed = Vector2(abs(pong_speed.x), pong_speed.y)
        # hit right pad: go left
        if(core.checkCollision(pong, pads[1]["object"])):
            pong_speed = Vector2(-abs(pong_speed.x), pong_speed.y)

        pass

def mouse_clicked(position):
    pass

def draw(screen):
    global current_scene
    if(current_scene == 1):
        for p in pads:
            p["object"].draw(screen)

        pong.draw(screen)
        pass

def drawBackground(screen, _):
    screen.fill((0, 0, 0))

def drawForeground(screen):
    pass

def button_pressed(button):
    global current_scene, start_button
    if(current_scene == 0 and button == start_button):
        core.log_message("button pressed!")
        current_scene = 1

        # unload start button
        start_button.unload()
        start_button = None
    else:
        core.log_message("wrong button pressed")

start_button = core.uiObject.button(core, (bounds[0] * 0.5, bounds[1] * 0.5), (bounds[0] / 2, bounds[1] / 2), (150, 50, 50), (220, 220, 220), "Start", button_pressed)

def drawUI(screen):
    global current_scene, player_scores
    if(current_scene == 0):
        start_button.draw(screen)

    elif(current_scene == 1):
        core.drawText(screen, f"P1: {player_scores[0]}", (0.1, 0.9), 70)
        core.drawText(screen, f"P2: {player_scores[1]}", (0.9, 0.9), 70)
        pass

    elif(current_scene == 2):
        global win_score
        if(player_scores[0] >= win_score):
            core.drawText(screen, f"P1 won", (0.5, 0.5), 200)
            core.drawText(screen, f"scores: P1: {player_scores[0]}, P2: {player_scores[1]}", (0.5, 0.75))
        if(player_scores[1] >= win_score):
            core.drawText(screen, f"P2 won", (0.5, 0.5), 200)
            core.drawText(screen, f"scores: P2: {player_scores[1]}, P1: {player_scores[0]}", (0.5, 0.75))

def GameLoad():
    core.debugCollisions(True)
    pass

if __name__ == "__main__":
    core.run(update, mouse_clicked, draw, drawBackground, drawForeground, drawUI, GameLoad)