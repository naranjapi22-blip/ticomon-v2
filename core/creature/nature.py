from dataclasses import dataclass

from .stat import Stat


@dataclass
class Nature:
    """
    Representa la naturaleza de una Creature.
    """

    name: str

    increased_stat: Stat | None
    decreased_stat: Stat | None

    def modifier_for(self, target_stat: Stat) -> float:
        if target_stat == self.increased_stat:
            return 1.1

        if target_stat == self.decreased_stat:
            return 0.9

        return 1.0