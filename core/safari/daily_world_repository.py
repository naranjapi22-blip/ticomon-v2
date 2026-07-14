from abc import ABC, abstractmethod
from datetime import date

from core.safari.daily_progress import SafariDailyWorld


class SafariDailyWorldRepository(ABC):
    @abstractmethod
    async def get_or_create(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> SafariDailyWorld:
        """Returns the daily world for a guild and cycle, creating it if needed."""

    @abstractmethod
    async def get_for_update(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> SafariDailyWorld:
        """Locks and returns the daily world for a guild and cycle."""

    @abstractmethod
    async def save(self, world: SafariDailyWorld) -> None:
        """Persists the daily world state."""

    @abstractmethod
    async def get(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> SafariDailyWorld | None:
        """Returns the persisted daily world for a guild and cycle, if any."""
