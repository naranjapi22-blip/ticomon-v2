from dataclasses import dataclass

from core.candy.candy_bundle import CandyBundle
from core.creature.creature import Creature


@dataclass(frozen=True)
class ReleaseResult:
    success: bool
    released_creatures: list[Creature]
    reward_bundle: CandyBundle
