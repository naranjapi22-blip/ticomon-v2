import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.db_config import close_pool, get_pool


async def create_collection_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trainer_collection_entries (
                    trainer_id BIGINT NOT NULL REFERENCES trainers(trainer_id),
                    species_id BIGINT NOT NULL REFERENCES species(id),
                    variant_id BIGINT NULL REFERENCES species_variants(id),
                    first_obtained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    source TEXT NOT NULL CHECK (source IN (
                        'starter', 'capture', 'safari', 'shop', 'evolution', 'trade',
                        'backfill'
                    ))
                )
                """)
            await connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                    trainer_collection_entries_canonical_unique_idx
                ON trainer_collection_entries (
                    trainer_id, species_id, COALESCE(variant_id, 0)
                )
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS trainer_collection_entries_trainer_idx
                ON trainer_collection_entries (trainer_id, first_obtained_at)
                """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trainer_collection_claims (
                    trainer_id BIGINT NOT NULL REFERENCES trainers(trainer_id),
                    collection_id TEXT NOT NULL,
                    milestone INTEGER NOT NULL CHECK (milestone > 0),
                    progress INTEGER NOT NULL CHECK (progress >= milestone),
                    rewarded_candies JSONB NOT NULL
                        CHECK (jsonb_typeof(rewarded_candies) = 'object'),
                    rewarded_mints INTEGER NOT NULL DEFAULT 0
                        CHECK (rewarded_mints >= 0),
                    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (trainer_id, collection_id, milestone)
                )
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS trainer_collection_claims_trainer_idx
                ON trainer_collection_claims (trainer_id, claimed_at)
                """)
    await close_pool()


if __name__ == "__main__":
    asyncio.run(create_collection_schema())
