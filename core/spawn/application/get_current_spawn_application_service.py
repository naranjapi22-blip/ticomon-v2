from core.spawn.session import SpawnSession
from core.spawn.spawn_session_repository import SpawnSessionRepository


class GetCurrentSpawnApplicationService:
    def __init__(
        self,
        spawn_session_repository: SpawnSessionRepository,
    ) -> None:
        self._spawn_session_repository = spawn_session_repository

    async def get_current(self) -> SpawnSession | None:
        return await self._spawn_session_repository.get_active()
