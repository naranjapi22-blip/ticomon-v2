from dataclasses import dataclass

from core.capture.domain.capture_attempt import CaptureAttempt
from core.creature.creature import Creature


@dataclass(frozen=True)
class CaptureResult:
    """
    Result of resolving a capture attempt.
    """

    attempt: CaptureAttempt

    success: bool

    creature: Creature | None
