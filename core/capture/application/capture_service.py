from core.capture.capture_result import CaptureResult
from core.capture.service import CaptureService
from core.creature.creature_repository import CreatureRepository
from core.spawn.exceptions import NoActiveSpawnSession
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
        opportunity_index: int,
    ) -> CaptureResult:
        session = await self._spawn_session_repository.get_active()

        if session is None:
            raise NoActiveSpawnSession()

        opportunity = session.get_opportunity(
            opportunity_index,
        )

        result = self._capture_service.capture(
            trainer_id=trainer_id,
            opportunity=opportunity,
        )

        if not result.success:
            return result

        session.remove_opportunity(
            opportunity_index,
        )

        assert result.creature is not None

        creature = await self._creature_repository.save(
            result.creature,
        )

        return CaptureResult(
            attempt=result.attempt,
            success=True,
            creature=creature,
        )
