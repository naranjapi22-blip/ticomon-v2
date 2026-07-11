import asyncio

from core.spawn.session import SpawnSession
from core.spawn.spawn_session_repository import (
    SpawnSessionRepository,
)


class InMemorySpawnSessionRepository(
    SpawnSessionRepository,
):
    """
    Stores the active spawn session for each guild.
    """

    def __init__(self) -> None:
        self._sessions: dict[int, SpawnSession] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    async def save(
        self,
        guild_id: int,
        session: SpawnSession,
    ) -> None:
        self._sessions[guild_id] = session

    async def get_active(
        self,
        guild_id: int,
    ) -> SpawnSession | None:
        return self._sessions.get(guild_id)

    async def clear(
        self,
        guild_id: int,
    ) -> None:
        self._sessions.pop(guild_id, None)

    def lock(
        self,
        guild_id: int,
    ) -> asyncio.Lock:
        return self._locks.setdefault(
            guild_id,
            asyncio.Lock(),
        )
