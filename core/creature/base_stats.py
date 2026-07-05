from core.creature.stat import Stat


class BaseStats:
    def __init__(
        self,
        hp: int,
        attack: int,
        defense: int,
        special_attack: int,
        special_defense: int,
        speed: int,
    ):
        self._stats = {
            Stat.HP: hp,
            Stat.ATTACK: attack,
            Stat.DEFENSE: defense,
            Stat.SPECIAL_ATTACK: special_attack,
            Stat.SPECIAL_DEFENSE: special_defense,
            Stat.SPEED: speed,
        }

    def for_stat(self, stat: Stat) -> int:
        return self._stats[stat]