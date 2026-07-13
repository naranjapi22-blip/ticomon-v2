import random

from core.capture.attempt_service import CaptureAttemptService
from core.capture.domain.capture_attempt import CaptureAttempt
from core.capture.domain.capture_ball_selector import CaptureBallSelector
from core.capture.domain.capture_chance_calculator import (
    CaptureChanceCalculator,
)
from core.capture.domain.capture_result import CaptureResult
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
        random_source: random.Random | None = None,
    ) -> None:
        self._ball_selector = ball_selector
        self._random_source = random_source or random
        self._attempt_service = CaptureAttemptService(chance_calculator)

    def capture(
        self,
        trainer_id: int,
        opportunity: Opportunity,
    ) -> CaptureResult:
        capture_ball = self._ball_selector.select()
        attempt_result = self._attempt_service.attempt(
            opportunity=opportunity,
            capture_ball=capture_ball,
            random_source=self._random_source,
        )

        attempt = CaptureAttempt(
            opportunity=opportunity,
            capture_ball=capture_ball,
            chance=attempt_result.chance,
        )

        if not attempt_result.success:
            opportunity.failed_attempts = attempt_result.opportunity.failed_attempts

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
