from dataclasses import dataclass

from core.achievement.unlock_result import AchievementUnlockResult
from core.candy.candy_bundle import CandyBundle
from core.capture.domain.capture_attempt import CaptureAttempt
from core.creature.creature import Creature


@dataclass(frozen=True)
class CaptureApplicationResult:
    """
    Result of executing the complete capture use case.
    """

    attempt: CaptureAttempt

    success: bool

    creature: Creature | None

    reward: CandyBundle

    achievements: tuple[AchievementUnlockResult, ...] = ()
