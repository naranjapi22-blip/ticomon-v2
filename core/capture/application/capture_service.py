from core.capture.capture_result import CaptureResult
from core.capture.service import CaptureService
from core.creature.creature_repository import CreatureRepository
from core.opportunity.opportunity import Opportunity


class CaptureApplicationService:
    """
    Executes the complete capture use case.
    """

    def __init__(
        self,
        capture_service: CaptureService,
        creature_repository: CreatureRepository,
    ) -> None:
        self._capture_service = capture_service
        self._creature_repository = creature_repository

    async def capture(
        self,
        trainer_id: str,
        opportunity: Opportunity,
    ) -> CaptureResult:

        result = self._capture_service.capture(
            trainer_id=trainer_id,
            opportunity=opportunity,
        )

        if not result.success:
            return result

        creature = await self._creature_repository.save(result.creature)

        return CaptureResult(
            success=True,
            creature=creature,
        )
