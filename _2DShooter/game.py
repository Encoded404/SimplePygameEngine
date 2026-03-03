import math
import random

from engine.core import Core, shapes, drawShape, Vector2
from scripts.enemy import SimpleEnemyScript
from scripts.bullet import BulletScript

bounds = (900 * 2, 600 * 1.5)
core = Core(bounds, 1, "2D shooter")

# player settings
player_size = 18
player_radius = player_size / 2
player_speed = 6
player_start_health = 100
player_color = (180, 220, 255)

# bullet settings
bullet_speed = 16
bullet_size = 10
bullet_color = (255, 220, 120)
bullet_damage = 1

# enemy settings
enemy_size = 30
enemy_speed = 2.6
enemy_health = 4
enemy_damage = 15
enemy_reward = 7
enemy_color = (255, 90, 90)
max_enemy_count = 3

player: Core.object | None = None
current_health = player_start_health
enemies: list[Core.object] = []
bullets: list[Core.object] = []


def get_player():
    return player


def hurt_player(damage: float):
    global current_health

    if current_health <= 0:
        return

    current_health = max(0, current_health - damage)
    if player:
        player.health = current_health

    if current_health <= 0 and core.running:
        core.log_message("Player defeated")
        core.stop()

def reward_money(amount: float):
    if amount == 0:
        return
    core.shared_state["money"] = core.shared_state.get("money", 0) + amount

def get_enemies():
    return enemies

def spawn_enemy(position: Vector2 | tuple[float, float] | None = None) -> Core.object:
    if position is None:
        position = Vector2(
            random.uniform(enemy_size, bounds[0] - enemy_size),
            random.uniform(enemy_size, bounds[1] - enemy_size),
        )

        while(position.distance_to(player.position) < 150):
            position = Vector2(
                random.uniform(enemy_size, bounds[0] - enemy_size),
                random.uniform(enemy_size, bounds[1] - enemy_size),
            )
    else:
        position = Vector2(position)

    enemy = core.object(
        core = core,
        shape = shapes.ELLIPSE,
        color = enemy_color,
        position = position.copy(),
        size = [enemy_size, enemy_size],
        scripts = [
            (
                SimpleEnemyScript,
                (),
                {
                    "target_getter": get_player,
                    "speed": enemy_speed,
                    "damage": enemy_damage,
                    "health": enemy_health,
                    "reward": enemy_reward,
                    "hurt_callback": hurt_player,
                },
            )
        ]
    )
    enemies.append(enemy)
    return enemy

def PlayerMovement():
    movement = Vector2(0.0, 0.0)
    speed_multiplier = 3 if core.isKeyPressed("shift") else 1

    if core.isKeyPressed("w"):
        movement.y -= 1
    if core.isKeyPressed("s"):
        movement.y += 1
    if core.isKeyPressed("a"):
        movement.x -= 1
    if core.isKeyPressed("d"):
        movement.x += 1

    movement = movement.normalized() * player_speed * speed_multiplier

    player.move(movement.x, movement.y)

def update():
    core.clean_object_list(enemies)
    core.clean_object_list(bullets)

    PlayerMovement()

    while len(enemies) < max_enemy_count:
        spawn_enemy()


def mouse_clicked(position):
    if player is None:
        return

    target_position = Vector2(position)
    direction_vector = target_position - player.position
    distance = direction_vector.length
    direction = 0
    if distance > 0:
        direction = math.atan2(direction_vector.y, direction_vector.x)

    

    rotation = math.degrees(direction)
    bullet = core.object(
        core = core,
        shape = shapes.CUSTOM,
        color = bullet_color,
        position = player.position.copy(),
        size = [bullet_size, bullet_size],
        scripts = [
            (
                BulletScript,
                (),
                {
                    "direction": direction,
                    "speed": bullet_speed,
                    "damage": bullet_damage,
                    "enemy_getter": get_enemies,
                },
            )
        ]
    )
    bullet.rotation = rotation
    bullets.append(bullet)


def drawBackground(screen, _):
    screen.fill((0, 0, 0))


def draw(screen):
    if player:
        player.draw(screen)
    for enemy in enemies:
        enemy.draw(screen)
    for bullet in bullets:
        bullet.draw(screen)


def drawUI(screen):
    money = core.shared_state.get("money", 0)
    core.drawText(screen, f"Health: {current_health}", (0.12, 0.08), 48)
    core.drawText(screen, f"Money: {money}", (0.12, 0.92), 40)
    core.drawText(screen, "WASD to move, click to shoot", (0.88, 0.92), 30)


def GameLoad():
    global player, current_health

    current_health = player_start_health
    core.shared_state["money"] = 0
    enemies.clear()
    bullets.clear()

    start_pos = Vector2(bounds[0] / 2, bounds[1] / 2)
    player = core.object(
        core,
        shapes.ELLIPSE,
        player_color,
        start_pos.copy(),
        [player_size, player_size],
        arguments={"role": "player"},
    )
    player.health = current_health
    player.set_move_restriction((player_radius, bounds[0] - player_radius), (player_radius, bounds[1] - player_radius))

    for _ in range(max_enemy_count):
        spawn_enemy()


if __name__ == "__main__":
    core.run(update, mouse_clicked, draw, drawBackground, None, drawUI, GameLoad)