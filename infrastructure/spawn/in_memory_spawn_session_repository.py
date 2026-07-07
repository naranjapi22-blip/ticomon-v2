from core.spawn.session import SpawnSession
from core.spawn.spawn_session_repository import (
    SpawnSessionRepository,
)


class InMemorySpawnSessionRepository(
    SpawnSessionRepository,
):
    """
    Stores the active spawn session in memory.
    """

    def __init__(self) -> None:
        self._session: SpawnSession | None = None

    async def save(
        self,
        session: SpawnSession,
    ) -> None:
        self._session = session

    async def get_active(
        self,
    ) -> SpawnSession | None:
        return self._session

    async def clear(
        self,
    ) -> None:
        self._session = None
