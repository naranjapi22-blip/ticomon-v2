import random

from core.capture.capture_result import CaptureResult
from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity import Opportunity


class CaptureService:
    """
    Domain service responsible for resolving a capture attempt.
    """

    def capture(
        self,
        trainer_id: str,
        opportunity: Opportunity,
    ) -> CaptureResult:
        success = random.random() < 0.5

        if not success:
            return CaptureResult(
                success=False,
                creature=None,
            )

        creature = CreatureFactory.create(
            trainer_id=trainer_id,
            opportunity=opportunity,
        )

        return CaptureResult(
            success=True,
            creature=creature,
        )
