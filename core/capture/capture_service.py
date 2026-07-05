import random

from core.opportunity.opportunity import Opportunity
from core.creature.creature_factory import CreatureFactory
from core.capture.capture_result import CaptureResult


class CaptureService:
    def capture(
        self,
        opportunity: Opportunity,
        trainer_id: str,
        creature_id: int,
    ) -> CaptureResult:

        success = random.random() < 0.5

        if not success:
            return CaptureResult(success=False, creature=None)

        creature = CreatureFactory.create(
            creature_id=creature_id,
            trainer_id=trainer_id,
            opportunity=opportunity,
        )

        return CaptureResult(success=True, creature=creature)