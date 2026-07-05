from dataclasses import dataclass

from .stat import Stat


@dataclass(frozen=True)
class IVs:
    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    def for_stat(self, stat: Stat) -> int:
        return {
            Stat.HP: self.hp,
            Stat.ATTACK: self.attack,
            Stat.DEFENSE: self.defense,
            Stat.SPECIAL_ATTACK: self.special_attack,
            Stat.SPECIAL_DEFENSE: self.special_defense,
            Stat.SPEED: self.speed,
        }[stat]