import asyncio
from textwrap import dedent

from infrastructure.db_config import close_pool, get_pool
from scripts.creature_schema import (
    ensure_creature_loadout_columns,
    ensure_creature_original_trainer_id,
)


async def create_safari_schema() -> None:
    """Creates the PostgreSQL structures required by persistent Safari state."""
    pool = await get_pool()

    async with pool.acquire() as connection:
        async with connection.transaction():
            await ensure_creature_loadout_columns(connection)
            await connection.execute(dedent("""
                    CREATE TABLE IF NOT EXISTS safari_daily_worlds (
                        guild_id BIGINT NOT NULL
                            CHECK (guild_id > 0),
                        cycle_date DATE NOT NULL,
                        daily_capture_count INTEGER NOT NULL DEFAULT 0
                            CHECK (daily_capture_count >= 0),
                        daily_unlock_count INTEGER NOT NULL DEFAULT 0
                            CHECK (
                                daily_unlock_count >= 0
                                AND daily_unlock_count <= 5
                            ),
                        current_influence JSONB NOT NULL DEFAULT '{}'::jsonb
                            CHECK (jsonb_typeof(current_influence) = 'object'),
                        PRIMARY KEY (guild_id, cycle_date)
                    )
                    """))
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS safari_daily_worlds_cycle_idx
                    ON safari_daily_worlds (cycle_date, guild_id)
                """)
            await connection.execute(dedent("""
                    CREATE TABLE IF NOT EXISTS safari_daily_active_trainers (
                        guild_id BIGINT NOT NULL
                            CHECK (guild_id > 0),
                        cycle_date DATE NOT NULL,
                        trainer_id BIGINT NOT NULL
                            CHECK (trainer_id > 0),
                        first_capture_at TIMESTAMPTZ NOT NULL,
                        PRIMARY KEY (guild_id, cycle_date, trainer_id)
                    )
                    """))
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS safari_daily_active_trainers_guild_cycle_idx
                    ON safari_daily_active_trainers (guild_id, cycle_date)
                """)
            await connection.execute("""
                ALTER TABLE safari_unlocks
                ADD COLUMN IF NOT EXISTS cycle_date DATE
                """)
            await connection.execute("""
                UPDATE safari_unlocks
                SET cycle_date = (unlocked_at AT TIME ZONE 'UTC')::date
                WHERE cycle_date IS NULL
                """)
            await connection.execute("""
                ALTER TABLE safari_unlocks
                ALTER COLUMN cycle_date SET NOT NULL
                """)
            await connection.execute("""
                ALTER TABLE safari_unlocks
                DROP CONSTRAINT IF EXISTS safari_unlocks_status_check
                """)
            await connection.execute("""
                ALTER TABLE safari_unlocks
                ADD CONSTRAINT safari_unlocks_status_check
                    CHECK (status IN ('AVAILABLE', 'EXPIRED', 'CONSUMED'))
                """)
            await connection.execute("""
                ALTER TABLE safari_unlocks
                DROP CONSTRAINT IF EXISTS safari_unlocks_valid_consumption
                """)
            await connection.execute("""
                ALTER TABLE safari_unlocks
                ADD CONSTRAINT safari_unlocks_valid_consumption
                    CHECK (
                        (
                            status = 'AVAILABLE'
                            AND consumed_at IS NULL
                            AND consumed_session_id IS NULL
                        )
                        OR
                        (
                            status = 'EXPIRED'
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
                """)
            duplicate_row = await connection.fetchrow("""
                SELECT guild_id, cycle_date, level, COUNT(*) AS count
                FROM safari_unlocks
                GROUP BY guild_id, cycle_date, level
                HAVING COUNT(*) > 1
                ORDER BY guild_id, cycle_date, level
                LIMIT 1
                """)
            if duplicate_row is not None:
                raise RuntimeError(
                    "Duplicate safari_unlocks rows exist for the same guild, "
                    "cycle_date and level. Resolve them before creating the "
                    "unique index.",
                )
            await connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS safari_unlocks_unique_cycle_level_idx
                    ON safari_unlocks (guild_id, cycle_date, level)
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS safari_unlocks_available_fifo_idx
                    ON safari_unlocks (
                        guild_id,
                        cycle_date,
                        unlocked_at,
                        id
                    )
                    WHERE status = 'AVAILABLE'
                """)
            await ensure_creature_original_trainer_id(connection)
            # The daily Safari tables are now authoritative; legacy world rows
            # are dropped instead of migrated.
            await connection.execute("""
                DROP TABLE IF EXISTS safari_worlds
                """)


async def main() -> None:
    await create_safari_schema()
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
