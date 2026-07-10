from dataclasses import dataclass

from core.candy.candy_bundle import CandyBundle
from core.creature.creature import Creature


@dataclass(frozen=True)
class PreviewReleaseResult:
    """
    Represents the result of previewing a release operation.
    """

    creatures: list[Creature]
    reward_bundle: CandyBundle
