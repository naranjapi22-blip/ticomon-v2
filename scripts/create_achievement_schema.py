import asyncio

from infrastructure.db_config import close_pool, get_pool


async def create_achievement_schema() -> None:
    """Creates the immutable achievement activity and unlock tables."""
    pool = await get_pool()

    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trainer_achievement_activities (
                    id BIGSERIAL PRIMARY KEY,
                    trainer_id BIGINT NOT NULL
                        REFERENCES trainers(trainer_id),
                    activity_type TEXT NOT NULL
                        CHECK (activity_type IN (
                            'capture',
                            'shiny_capture',
                            'species_discovered',
                            'evolution',
                            'release',
                            'completed_trade',
                            'safari_participation',
                            'safari_capture'
                        )),
                    species_id BIGINT NULL
                        REFERENCES species(id),
                    source TEXT NULL
                        CHECK (source IS NULL OR source IN ('normal', 'safari')),
                    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    idempotency_key TEXT NOT NULL,
                    CONSTRAINT trainer_achievement_activity_species_required
                        CHECK (
                            activity_type NOT IN (
                                'capture',
                                'shiny_capture',
                                'species_discovered',
                                'safari_capture'
                            )
                            OR species_id IS NOT NULL
                        ),
                    UNIQUE (trainer_id, activity_type, idempotency_key)
                )
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS trainer_achievement_activities_progress_idx
                ON trainer_achievement_activities (
                    trainer_id,
                    activity_type,
                    occurred_at
                )
                """)
            await connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                    trainer_achievement_discovered_species_unique_idx
                ON trainer_achievement_activities (trainer_id, species_id)
                WHERE activity_type = 'species_discovered'
                """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trainer_achievement_unlocks (
                    trainer_id BIGINT NOT NULL
                        REFERENCES trainers(trainer_id),
                    achievement_id TEXT NOT NULL,
                    unlocked_at TIMESTAMPTZ NOT NULL,
                    rewarded_candies JSONB NOT NULL
                        CHECK (jsonb_typeof(rewarded_candies) = 'object'),
                    PRIMARY KEY (trainer_id, achievement_id)
                )
                """)

    await close_pool()


async def main() -> None:
    await create_achievement_schema()


if __name__ == "__main__":
    asyncio.run(main())
