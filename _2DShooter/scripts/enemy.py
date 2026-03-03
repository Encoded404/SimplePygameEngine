import math
from typing import Callable
from engine.core import Core

class SimpleEnemyScript:
    def __init__(
        self,
        target_getter: Callable[[], "object"],
        hurt_callback: Callable[[float], None] | None = None,
        speed: float = 2.6,
        damage: float = 15,
        health: float = 4,
        reward: float = 7,
    ):
        self._target_getter = target_getter
        self.speed = speed
        self.attack_damage = damage
        self.health = health
        self.reward = reward
        self.hurt_callback = hurt_callback

    def ready(self, obj):
        obj.health = self.health
        obj.damage = self.damage
        obj.reward = self.reward

    def update(self, obj):
        target = self._target_getter()
        if target is None:
            return

        dir = (target.position[0] - obj.position[0], target.position[1] - obj.position[1])
        dir = Core.normalize(dir)        

        obj.position[0] += dir[0] * self.speed
        obj.position[1] += dir[1] * self.speed

        if obj.core.checkCollision(obj, target):
            if callable(self.hurt_callback):
                self.hurt_callback(self.attack_damage)
            obj.destroy()

    def damage(self, amount: float):
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.core.shared_state["money"] = self.core.shared_state.get("money", 0) + self.reward
            self.object.destroy()
            return True
        return False
            
