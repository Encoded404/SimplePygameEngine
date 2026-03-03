import math
from typing import Callable

from engine.core import shapes, drawShape, Core

class BulletScript:
    def __init__(
        self,
        direction: tuple[float, float],
        enemy_getter: Callable[[], list] | None = None,
        speed: float = 16,
        damage: float = 1,
        lifetime: int = 180,
    ):
        self.direction = direction
        self.speed = speed
        self.damage = damage
        self.lifetime = lifetime
        self.attack_age = 0
        self.enemy_getter = enemy_getter

    def ready(self, obj):
        obj.rotation = self.direction
        obj.speed = self.speed

    def update(self, obj):
        obj.position[0] += math.cos(self.direction) * self.speed
        obj.position[1] += math.sin(self.direction) * self.speed
        self.attack_age += 1

        # destroy the bullet if it goes off-screen or exceeds its lifetime
        if (
            obj.position[0] < 0
            or obj.position[0] > obj.core.screenSize[0]
            or obj.position[1] < 0
            or obj.position[1] > obj.core.screenSize[1]
            
            or self.attack_age > self.lifetime
        ):
            obj.destroy()
            return

        enemies = self.enemy_getter()
        for enemy in list(enemies):
            if enemy not in obj.core._objects:
                continue
            if obj.core.checkCollision(obj, enemy):
                if Core.has_function(enemy, "damage"):
                    enemy.damage(self.damage)
                else:
                    obj.core.log_message("Enemy does not have damage function!", True)

                obj.destroy()
                return

    def draw(self, screen, obj):
        drawShape(screen, shapes.ELLIPSE, obj.color, obj.position, obj.size)

    def getColliders(self, obj):
        return [
            {
                "shape": shapes.ELLIPSE,
                "offset": (0, 0),
                "size": obj.size,
            }
        ]