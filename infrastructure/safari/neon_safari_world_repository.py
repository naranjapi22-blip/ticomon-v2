from core.safari.world import SafariWorld
from core.safari.world_repository import SafariWorldRepository
from infrastructure.db_config import get_pool
from infrastructure.safari.world_mapper import SafariWorldMapper


class NeonSafariWorldRepository(SafariWorldRepository):
    def __init__(self) -> None:
        self._mapper = SafariWorldMapper()

    async def save(self, world: SafariWorld) -> SafariWorld:
        pool = await get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                INSERT INTO safari_worlds (
                    guild_id,
                    current_progress,
                    daily_unlock_count,
                    current_influence,
                    last_daily_reset_date
                )
                VALUES ($1, $2, $3, $4::jsonb, $5)
                ON CONFLICT (guild_id) DO UPDATE
                SET
                    current_progress = EXCLUDED.current_progress,
                    daily_unlock_count = EXCLUDED.daily_unlock_count,
                    current_influence = EXCLUDED.current_influence,
                    last_daily_reset_date = EXCLUDED.last_daily_reset_date
                RETURNING *
                """,
                *self._mapper.to_row(world),
            )

        assert row is not None
        return self._mapper.from_row(row)

    async def get_by_guild_id(self, guild_id: int) -> SafariWorld | None:
        if guild_id <= 0:
            raise ValueError("guild_id must be positive.")

        pool = await get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT *
                FROM safari_worlds
                WHERE guild_id = $1
                """,
                guild_id,
            )

        return self._mapper.from_row(row) if row is not None else None
