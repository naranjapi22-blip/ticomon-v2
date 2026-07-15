from dataclasses import dataclass

from core.candy.candy_bundle import CandyBundle


@dataclass(frozen=True, slots=True)
class AchievementUnlockResult:
    """An achievement unlocked as the result of one completed action."""

    achievement_id: str
    rewarded_candies: CandyBundle
