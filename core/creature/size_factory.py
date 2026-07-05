import random

from core.creature.size import Size


class SizeFactory:
    @staticmethod
    def create() -> Size:
        value = random.gauss(1.0, 0.15)
        value = max(0.5, min(1.5, value))
        return Size(round(value, 2))