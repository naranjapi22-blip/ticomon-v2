"""Idempotently backfill valid Gen 9 abilities and initial movesets."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.battle.poke_env.loadout_catalog import (  # noqa: E402
    PokeEnvLoadoutCatalog,
)
from infrastructure.db_config import close_pool, get_pool  # noqa: E402
from infrastructure.species.neon_species_repository import (  # noqa: E402
    NeonSpeciesRepository,
)

logger = logging.getLogger(__name__)


async def migrate(dry_run: bool = False, batch_size: int = 250) -> dict[str, int]:
    pool = await get_pool()
    species_repository = NeonSpeciesRepository()
    catalog = PokeEnvLoadoutCatalog()
    summary = {"reviewed": 0, "assigned": 0, "skipped": 0, "errors": 0}
    try:
        async with pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT id, species_id, ability_id, equipped_moves
                FROM creatures
                ORDER BY id
                """)
            species_by_id = {
                item.id: item
                for item in await species_repository.get_many(
                    list({row["species_id"] for row in rows})
                )
            }
            for start in range(0, len(rows), batch_size):
                batch = rows[start : start + batch_size]
                async with connection.transaction():
                    for row in batch:
                        summary["reviewed"] += 1
                        try:
                            species = species_by_id.get(row["species_id"])
                            if species is None:
                                summary["skipped"] += 1
                                logger.warning(
                                    "Species %s was not found for creature %s",
                                    row["species_id"],
                                    row["id"],
                                )
                                continue
                            abilities = catalog.abilities_for(species)
                            valid = {ability.id for ability in abilities}
                            ability_id = row["ability_id"]
                            moves = tuple(row["equipped_moves"] or ())
                            if ability_id in valid and moves:
                                continue
                            if not abilities:
                                summary["skipped"] += 1
                                logger.warning(
                                    "No ability catalog for species %s", species.id
                                )
                                continue
                            ability_id = (
                                ability_id if ability_id in valid else abilities[0].id
                            )
                            moves = moves or catalog.initial_moves(
                                species, seed=row["id"]
                            )
                            if not dry_run:
                                await connection.execute(
                                    """
                                    UPDATE creatures
                                    SET ability_id = $1, equipped_moves = $2
                                    WHERE id = $3
                                    """,
                                    ability_id,
                                    list(moves),
                                    row["id"],
                                )
                            summary["assigned"] += 1
                        except Exception:
                            summary["errors"] += 1
                            logger.exception("Could not migrate creature %s", row["id"])
    finally:
        await close_pool()
    return summary


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=250)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    print(await migrate(dry_run=args.dry_run, batch_size=args.batch_size))


if __name__ == "__main__":
    asyncio.run(main())
