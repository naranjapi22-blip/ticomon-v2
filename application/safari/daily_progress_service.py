from __future__ import annotations

from datetime import UTC, date, datetime

from core.safari.daily_active_trainer_repository import (
    SafariDailyActiveTrainerRepository,
)
from core.safari.daily_progress import (
    SafariDailyProgressService,
    SafariDailyProgressSnapshot,
)
from core.safari.daily_world_repository import SafariDailyWorldRepository


class GetSafariDailyProgressApplicationService:
    def __init__(
        self,
        daily_world_repository: SafariDailyWorldRepository,
        daily_active_trainer_repository: SafariDailyActiveTrainerRepository,
        daily_progress_service: SafariDailyProgressService,
    ) -> None:
        self._daily_world_repository = daily_world_repository
        self._daily_active_trainer_repository = daily_active_trainer_repository
        self._daily_progress_service = daily_progress_service

    async def get(
        self,
        guild_id: int,
        cycle_date: date | None = None,
    ) -> SafariDailyProgressSnapshot:
        if cycle_date is None:
            cycle_date = datetime.now(UTC).date()

        world = await self._daily_world_repository.get_or_create(guild_id, cycle_date)
        active_player_count = await self._daily_active_trainer_repository.count_active(
            guild_id,
            cycle_date,
        )
        return self._daily_progress_service.snapshot(world, active_player_count)
