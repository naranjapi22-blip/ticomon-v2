import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.db_config import close_pool, get_pool  # noqa: E402


async def create_team_schema() -> None:
    """Creates the PostgreSQL structures required by the Team module."""

    pool = await get_pool()

    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS trainer_team_slots (
                    id BIGSERIAL PRIMARY KEY,
                    trainer_id BIGINT NOT NULL,
                    slot INTEGER NOT NULL,
                    creature_id BIGINT NOT NULL
                        REFERENCES creatures(id),
                    CONSTRAINT trainer_team_slots_valid_slot
                        CHECK (slot >= 1 AND slot <= 9),
                    CONSTRAINT trainer_team_slots_unique_slot
                        UNIQUE (trainer_id, slot),
                    CONSTRAINT trainer_team_slots_unique_creature
                        UNIQUE (trainer_id, creature_id)
                )
                """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS trainer_team_slots_trainer_idx
                ON trainer_team_slots (trainer_id)
                """)

    await close_pool()


async def main() -> None:
    await create_team_schema()
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
