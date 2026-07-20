"""Repair persisted move PP from the installed poke-env catalog.

This is a one-time data repair for databases written by the old ``Move.pp``
reader. It is intentionally separate from deploy schema creation and catalog
synchronization.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from poke_env.battle.move import Move

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.db_config import close_pool, get_pool  # noqa: E402


async def repair_move_pp(*, dry_run: bool = False) -> dict[str, int]:
    pool = await get_pool()
    repaired = skipped = 0
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch("SELECT id FROM moves ORDER BY id")
            updates = []
            for row in rows:
                try:
                    pp = int(getattr(Move(row["id"], gen=9), "max_pp"))
                except (KeyError, TypeError, ValueError):
                    skipped += 1
                    continue
                updates.append((row["id"], pp))
            if not dry_run:
                async with connection.transaction():
                    await connection.executemany(
                        "UPDATE moves SET pp = $2 WHERE id = $1", updates
                    )
            repaired = len(updates)
    finally:
        await close_pool()
    return {"repaired": repaired, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair persisted move PP values.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(asyncio.run(repair_move_pp(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
