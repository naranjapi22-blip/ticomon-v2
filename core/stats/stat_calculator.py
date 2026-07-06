from math import floor

from core.creature.creature import Creature
from core.creature.stat import Stat


class StatCalculator:
    """Conoce la regla para calcular las estadísticas de una Creature."""

    LEVEL = 50

    def calculate(self, creature: Creature, stat: Stat) -> int:
        base = creature.stat_for(stat)
        iv = creature.iv_for(stat)

        if stat == Stat.HP:
            return floor(((2 * base + iv) * self.LEVEL) / 100) + self.LEVEL + 10

        value = floor(((2 * base + iv) * self.LEVEL) / 100) + 5

        return floor(value * creature.nature_modifier_for(stat))
