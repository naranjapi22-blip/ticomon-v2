from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from core.safari.unlock import SafariUnlock


class SafariUnlockRepository(ABC):
    @abstractmethod
    async def save(self, unlock: SafariUnlock) -> SafariUnlock:
        """Persists an unlock and returns its stored state."""

    @abstractmethod
    async def get_available_by_guild_id(
        self,
        guild_id: int,
    ) -> tuple[SafariUnlock, ...]:
        """Returns available unlocks for a guild in FIFO order."""

    @abstractmethod
    async def consume_next(
        self,
        guild_id: int,
        consumed_at: datetime,
        consumed_session_id: UUID,
    ) -> SafariUnlock | None:
        """Atomically consumes and returns the next available unlock."""
