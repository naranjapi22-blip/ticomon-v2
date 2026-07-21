"""Report creatures whose persisted PvP loadout is invalid for its species."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.db_config import close_pool, get_pool  # noqa: E402


async def diagnose(trainer_id: int | None = None) -> list[dict]:
    pool = await get_pool()
    try:
        where = "WHERE c.trainer_id = $1" if trainer_id is not None else ""
        args = (trainer_id,) if trainer_id is not None else ()
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                f"""
                SELECT c.id, c.trainer_id, c.collection_number, c.species_id,
                       s.name AS species_name, c.ability_id, c.equipped_moves,
                       EXISTS (
                           SELECT 1 FROM species_abilities sa
                           WHERE sa.species_id = c.species_id
                             AND sa.ability_id = c.ability_id
                       ) AS ability_valid,
                       ARRAY(
                           SELECT requested.move_id
                           FROM unnest(COALESCE(c.equipped_moves,
                                                ARRAY[]::text[])) requested(move_id)
                           WHERE NOT EXISTS (
                               SELECT 1 FROM species_moves sm
                               WHERE sm.species_id = c.species_id
                                 AND sm.move_id = requested.move_id
                           )
                       ) AS illegal_moves
                FROM creatures c
                JOIN species s ON s.id = c.species_id
                {where}
                ORDER BY c.id
                """,
                *args,
            )
        return [dict(row) for row in rows]
    finally:
        await close_pool()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trainer-id", type=int)
    args = parser.parse_args()
    print(json.dumps(await diagnose(args.trainer_id), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
