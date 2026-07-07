import random

from core.capture.capture_result import CaptureResult
from core.capture.domain.capture_attempt import CaptureAttempt
from core.capture.domain.capture_ball_selector import CaptureBallSelector
from core.capture.domain.capture_chance_calculator import (
    CaptureChanceCalculator,
)
from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity import Opportunity


class CaptureService:
    """
    Domain service responsible for resolving a capture attempt.
    """

    def __init__(
        self,
        chance_calculator: CaptureChanceCalculator,
        ball_selector: CaptureBallSelector,
    ) -> None:
        self._chance_calculator = chance_calculator
        self._ball_selector = ball_selector

    def capture(
        self,
        trainer_id: int,
        opportunity: Opportunity,
    ) -> CaptureResult:
        capture_ball = self._ball_selector.select()

        chance = self._chance_calculator.calculate(
            opportunity=opportunity,
            capture_ball=capture_ball,
        )

        attempt = CaptureAttempt(
            opportunity=opportunity,
            capture_ball=capture_ball,
            chance=chance,
        )

        success = random.random() < attempt.chance

        if not success:
            opportunity.failed_attempts += 1

            return CaptureResult(
                attempt=attempt,
                success=False,
                creature=None,
            )

        creature = CreatureFactory.create(
            trainer_id=trainer_id,
            opportunity=opportunity,
        )

        return CaptureResult(
            attempt=attempt,
            success=True,
            creature=creature,
        )
