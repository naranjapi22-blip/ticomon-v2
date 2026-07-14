from __future__ import annotations

from datetime import UTC, date, datetime

from core.safari.daily_active_trainer_repository import (
    SafariDailyActiveTrainerRepository,
)
from infrastructure.db_config import get_pool


class NeonSafariDailyActiveTrainerRepository(SafariDailyActiveTrainerRepository):
    async def register_if_absent(
        self,
        guild_id: int,
        cycle_date: date,
        trainer_id: int,
        first_capture_at: datetime,
    ) -> bool:
        self._validate_guild_id(guild_id)
        self._validate_guild_id(trainer_id, field_name="trainer_id")
        if cycle_date is None:
            raise ValueError("cycle_date is required.")

        pool = await get_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO safari_daily_active_trainers (
                    guild_id,
                    cycle_date,
                    trainer_id,
                    first_capture_at
                )
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (guild_id, cycle_date, trainer_id) DO NOTHING
                RETURNING trainer_id
                """,
                guild_id,
                cycle_date,
                trainer_id,
                self._as_utc(first_capture_at),
            )

        return row is not None

    async def count_active(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> int:
        self._validate_guild_id(guild_id)
        if cycle_date is None:
            raise ValueError("cycle_date is required.")

        pool = await get_pool()
        async with pool.acquire() as connection:
            value = await connection.fetchval(
                """
                SELECT COUNT(*)
                FROM safari_daily_active_trainers
                WHERE guild_id = $1
                  AND cycle_date = $2
                """,
                guild_id,
                cycle_date,
            )

        return int(value or 0)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value is None:
            raise ValueError("first_capture_at is required.")
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _validate_guild_id(value: int, *, field_name: str = "guild_id") -> None:
        if value <= 0:
            raise ValueError(f"{field_name} must be positive.")
