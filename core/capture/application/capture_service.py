from core.capture.domain.capture_result import CaptureResult
from core.capture.service import CaptureService
from core.creature.creature_repository import CreatureRepository
from core.spawn.exceptions import (
    NoActiveSpawnSession,
    NoSelectedOpportunity,
)
from core.spawn.spawn_session_repository import SpawnSessionRepository


class CaptureApplicationService:
    """
    Executes the complete capture use case.
    """

    def __init__(
        self,
        capture_service: CaptureService,
        creature_repository: CreatureRepository,
        spawn_session_repository: SpawnSessionRepository,
    ) -> None:
        self._capture_service = capture_service
        self._creature_repository = creature_repository
        self._spawn_session_repository = spawn_session_repository

    async def capture(
        self,
        trainer_id: int,
    ) -> CaptureResult:
        session = await self._spawn_session_repository.get_active()

        if session is None:
            raise NoActiveSpawnSession()

        if session.selected_opportunity is None:
            raise NoSelectedOpportunity()

        result = self._capture_service.capture(
            trainer_id=trainer_id,
            opportunity=session.selected_opportunity,
        )

        if not result.success:
            return result

        assert result.creature is not None

        creature = await self._creature_repository.save(
            result.creature,
        )

        await self._spawn_session_repository.clear()

        return CaptureResult(
            attempt=result.attempt,
            success=True,
            creature=creature,
        )
