from dataclasses import dataclass, field
from typing import Protocol

from core.battle.engine.battle_fighter import BattleFighter


class RandomSource(Protocol):
    def randint(self, a: int, b: int) -> int: ...

    def random(self) -> float: ...

    def sample(self, population: list, k: int) -> list: ...


@dataclass
class BattleSideState:
    name: str
    fighters: tuple[BattleFighter, ...]
    hp: list[int] = field(default_factory=list)
    hp_max: list[int] = field(default_factory=list)
    active_index: int = 0

    def __post_init__(self) -> None:
        if not self.hp:
            self.hp = [fighter.hp_max for fighter in self.fighters]
        if not self.hp_max:
            self.hp_max = [fighter.hp_max for fighter in self.fighters]

    @property
    def active(self) -> BattleFighter:
        return self.fighters[self.active_index]

    @property
    def total_hp(self) -> int:
        return sum(self.hp)

    def has_bench(self) -> bool:
        return self.active_index < len(self.fighters) - 1

    def switch_to_next(self) -> BattleFighter | None:
        if not self.has_bench():
            return None

        self.active_index += 1
        return self.active

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "active_index": self.active_index,
            "hp": list(self.hp),
            "hp_max": list(self.hp_max),
            "active_name": self.active.display_name,
            "active_move": self.active.move_display_name,
        }
