from abc import ABC, abstractmethod
from datetime import date, datetime


class SafariDailyActiveTrainerRepository(ABC):
    @abstractmethod
    async def register_if_absent(
        self,
        guild_id: int,
        cycle_date: date,
        trainer_id: int,
        first_capture_at: datetime,
    ) -> bool:
        """Registers an active trainer if they were not already counted."""

    @abstractmethod
    async def count_active(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> int:
        """Returns the number of unique active trainers for a guild and cycle."""
