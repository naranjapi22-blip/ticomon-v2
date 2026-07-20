import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.db_config import close_pool, get_pool  # noqa: E402
from scripts.creature_schema import ensure_creature_loadout_columns  # noqa: E402


async def create_creature_loadout_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await ensure_creature_loadout_columns(connection)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS abilities (
                    id TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    generation INTEGER NOT NULL DEFAULT 9,
                    metadata_json JSONB
                )
                """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS species_abilities (
                    species_id BIGINT NOT NULL REFERENCES species(id),
                    ability_id TEXT NOT NULL REFERENCES abilities(id),
                    slot INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 3),
                    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
                    PRIMARY KEY (species_id, ability_id),
                    UNIQUE (species_id, slot)
                )
                """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS moves (
                    id TEXT PRIMARY KEY,
                    canonical_name TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    power INTEGER,
                    accuracy INTEGER,
                    pp INTEGER NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    generation INTEGER NOT NULL DEFAULT 9,
                    metadata_json JSONB
                )
                """)
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS species_moves (
                    species_id BIGINT NOT NULL REFERENCES species(id),
                    move_id TEXT NOT NULL REFERENCES moves(id),
                    acquisition_method TEXT,
                    generation INTEGER,
                    PRIMARY KEY (species_id, move_id)
                )
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS species_abilities_species_idx
                ON species_abilities (species_id)
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS species_moves_species_idx
                ON species_moves (species_id)
                """)
    await close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create idempotent creature ability and moveset tables."
    )
    parser.parse_args()
    asyncio.run(create_creature_loadout_schema())


if __name__ == "__main__":
    main()
