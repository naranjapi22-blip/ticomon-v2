from dataclasses import dataclass

from core.capture.domain.capture_ball import CaptureBall
from core.opportunity.opportunity import Opportunity


@dataclass(frozen=True)
class CaptureAttempt:
    """
    Represents a single capture attempt.
    """

    opportunity: Opportunity

    capture_ball: CaptureBall

    chance: float
