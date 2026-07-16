import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from infrastructure.db_config import close_pool
from infrastructure.persistence.repositories.neon_collection_history_repository import (
    NeonCollectionHistoryRepository,
)


async def main() -> None:
    created = await NeonCollectionHistoryRepository().backfill_existing_creatures()
    print(f"Backfilled {created} collection entries.")
    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
