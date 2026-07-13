from abc import ABC, abstractmethod

from core.safari.world import SafariWorld


class SafariWorldRepository(ABC):
    @abstractmethod
    async def save(self, world: SafariWorld) -> SafariWorld:
        """Persists and returns the current world state for a guild."""

    @abstractmethod
    async def get_by_guild_id(self, guild_id: int) -> SafariWorld | None:
        """Returns the persisted world for a guild, if one exists."""
