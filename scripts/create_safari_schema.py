import asyncio

from infrastructure.db_config import close_pool, get_pool
from scripts.creature_schema import ensure_creature_original_trainer_id


async def create_safari_schema() -> None:
    """Creates the PostgreSQL structures required by persistent Safari state."""
    pool = await get_pool()

    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS safari_worlds (
                    guild_id BIGINT PRIMARY KEY
                        CHECK (guild_id > 0),
                    current_progress INTEGER NOT NULL
                        CHECK (current_progress >= 0),
                    daily_unlock_count INTEGER NOT NULL
                        CHECK (daily_unlock_count >= 0),
                    current_influence JSONB NOT NULL DEFAULT '{}'::jsonb
                        CHECK (jsonb_typeof(current_influence) = 'object'),
                    last_daily_reset_date DATE NOT NULL
                )
                """
            )
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS safari_unlocks (
                    id BIGSERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL CHECK (guild_id > 0),
                    level SMALLINT NOT NULL CHECK (level > 0),
                    encounter_count INTEGER NOT NULL
                        CHECK (encounter_count > 0),
                    balls_per_participant INTEGER NOT NULL
                        CHECK (balls_per_participant > 0),
                    map_influence JSONB NOT NULL DEFAULT '{}'::jsonb
                        CHECK (jsonb_typeof(map_influence) = 'object'),
                    status VARCHAR(20) NOT NULL
                        CHECK (status IN ('AVAILABLE', 'CONSUMED')),
                    unlocked_at TIMESTAMPTZ NOT NULL,
                    consumed_at TIMESTAMPTZ NULL,
                    consumed_session_id UUID NULL,
                    CONSTRAINT safari_unlocks_valid_consumption
                        CHECK (
                            (
                                status = 'AVAILABLE'
                                AND consumed_at IS NULL
                                AND consumed_session_id IS NULL
                            )
                            OR
                            (
                                status = 'CONSUMED'
                                AND consumed_at IS NOT NULL
                                AND consumed_session_id IS NOT NULL
                            )
                        )
                )
                """
            )
            await connection.execute(
                """
                CREATE INDEX IF NOT EXISTS safari_unlocks_available_fifo_idx
                ON safari_unlocks (guild_id, unlocked_at, id)
                WHERE status = 'AVAILABLE'
                """
            )
            await ensure_creature_original_trainer_id(connection)


async def main() -> None:
    await create_safari_schema()
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
