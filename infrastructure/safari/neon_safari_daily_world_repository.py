from __future__ import annotations

from datetime import date

from core.safari.daily_progress import SafariDailyWorld
from core.safari.daily_world_repository import SafariDailyWorldRepository
from infrastructure.db_config import get_pool
from infrastructure.safari.daily_world_mapper import SafariDailyWorldMapper


class NeonSafariDailyWorldRepository(SafariDailyWorldRepository):
    def __init__(self) -> None:
        self._mapper = SafariDailyWorldMapper()

    async def get_or_create(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> SafariDailyWorld:
        world = SafariDailyWorld.create(guild_id, cycle_date)
        pool = await get_pool()

        async with pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO safari_daily_worlds (
                    guild_id,
                    cycle_date,
                    daily_capture_count,
                    daily_unlock_count,
                    current_influence
                )
                VALUES ($1, $2, $3, $4, $5::jsonb)
                ON CONFLICT (guild_id, cycle_date) DO NOTHING
                """,
                *self._mapper.to_row(world),
            )
            row = await connection.fetchrow(
                """
                SELECT *
                FROM safari_daily_worlds
                WHERE guild_id = $1
                  AND cycle_date = $2
                FOR UPDATE
                """,
                guild_id,
                cycle_date,
            )

        assert row is not None
        return self._mapper.from_row(row)

    async def get_for_update(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> SafariDailyWorld:
        row = await self._select(guild_id, cycle_date, for_update=True)
        if row is None:
            raise ValueError("Safari daily world was not found.")
        return self._mapper.from_row(row)

    async def save(self, world: SafariDailyWorld) -> None:
        pool = await get_pool()

        async with pool.acquire() as connection:
            result = await connection.execute(
                """
                INSERT INTO safari_daily_worlds (
                    guild_id,
                    cycle_date,
                    daily_capture_count,
                    daily_unlock_count,
                    current_influence
                )
                VALUES ($1, $2, $3, $4, $5::jsonb)
                ON CONFLICT (guild_id, cycle_date) DO UPDATE
                SET
                    daily_capture_count = EXCLUDED.daily_capture_count,
                    daily_unlock_count = EXCLUDED.daily_unlock_count,
                    current_influence = EXCLUDED.current_influence
                """,
                *self._mapper.to_row(world),
            )

        assert result is not None

    async def get(
        self,
        guild_id: int,
        cycle_date: date,
    ) -> SafariDailyWorld | None:
        row = await self._select(guild_id, cycle_date, for_update=False)
        return self._mapper.from_row(row) if row is not None else None

    async def _select(
        self,
        guild_id: int,
        cycle_date: date,
        *,
        for_update: bool,
    ):
        pool = await get_pool()
        query = """
            SELECT *
            FROM safari_daily_worlds
            WHERE guild_id = $1
              AND cycle_date = $2
        """
        if for_update:
            query += " FOR UPDATE"

        async with pool.acquire() as connection:
            return await connection.fetchrow(query, guild_id, cycle_date)
