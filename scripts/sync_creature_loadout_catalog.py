"""Synchronize Gen 9 Showdown abilities and learnsets into PostgreSQL."""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Iterable

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

CATALOG_BATCH_SIZE = 500
RELATIONSHIP_BATCH_SIZE = 500
PROGRESS_INTERVAL = 50


ABILITY_INSERT = """
    INSERT INTO abilities (id, canonical_name, display_name)
    VALUES ($1, $1, $2)
    ON CONFLICT (id) DO UPDATE SET
        display_name = EXCLUDED.display_name
    """

MOVE_INSERT = """
    INSERT INTO moves
        (id, canonical_name, display_name, type, category, power, accuracy, pp,
         priority)
    VALUES ($1, $1, $2, $3, $4, $5, $6, $7, $8)
    ON CONFLICT (id) DO UPDATE SET
        display_name = EXCLUDED.display_name,
        type = EXCLUDED.type, category = EXCLUDED.category,
        power = EXCLUDED.power, accuracy = EXCLUDED.accuracy,
        pp = EXCLUDED.pp, priority = EXCLUDED.priority
    """

SPECIES_ABILITY_INSERT = """
    INSERT INTO species_abilities
        (species_id, ability_id, slot, is_hidden)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (species_id, ability_id) DO UPDATE
    SET slot = EXCLUDED.slot, is_hidden = EXCLUDED.is_hidden
    """

SPECIES_MOVE_INSERT = """
    INSERT INTO species_moves (species_id, move_id, generation)
    VALUES ($1, $2, 9)
    ON CONFLICT (species_id, move_id) DO NOTHING
    """


def _batches(items: Iterable[tuple], size: int):
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _print_progress(summary: dict[str, int]) -> None:
    print(
        "Catalog progress: "
        f"species={summary['species']} "
        f"abilities_found={summary['abilities']} "
        f"moves_found={summary['moves']} "
        f"rows_written={summary['rows_written']}",
        flush=True,
    )


async def _write_batches(
    connection,
    query: str,
    rows,
    summary: dict[str, int],
    *,
    batch_size: int,
) -> None:
    for batch in _batches(rows, batch_size):
        async with connection.transaction():
            await connection.executemany(query, batch)
        summary["rows_written"] += len(batch)


async def sync_catalog(*, dry_run: bool = False) -> dict[str, int]:
    pool = await get_pool()
    species_repository = NeonSpeciesRepository()
    catalog = PokeEnvLoadoutCatalog()
    summary = {
        "species": 0,
        "abilities": 0,
        "moves": 0,
        "species_without_abilities": 0,
        "species_without_moves": 0,
        "rows_written": 0,
    }
    try:
        species = await species_repository.get_all()
        abilities_by_id = {}
        moves_by_id = {}
        species_abilities = {}
        species_moves = {}
        for item in species:
            abilities = catalog.abilities_for(item)
            moves = catalog.moves_for(item)
            summary["species"] += 1
            summary["abilities"] += len(abilities)
            summary["moves"] += len(moves)
            summary["species_without_abilities"] += not bool(abilities)
            summary["species_without_moves"] += not bool(moves)
            for ability in abilities:
                abilities_by_id[ability.id] = ability
                species_abilities[(item.id, ability.id)] = (
                    item.id,
                    ability.id,
                    ability.slot,
                    ability.is_hidden,
                )
            for move in moves:
                moves_by_id[move.id] = move
                species_moves[(item.id, move.id)] = (item.id, move.id)
            if summary["species"] % PROGRESS_INTERVAL == 0:
                _print_progress(summary)

        if not dry_run:
            async with pool.acquire() as connection:
                ability_rows = [
                    (ability.id, ability.display_name)
                    for ability in abilities_by_id.values()
                ]
                await _write_batches(
                    connection,
                    ABILITY_INSERT,
                    ability_rows,
                    summary,
                    batch_size=CATALOG_BATCH_SIZE,
                )

                move_rows = [
                    (
                        move.id,
                        move.display_name,
                        move.move_type,
                        move.category,
                        move.base_power,
                        move.accuracy,
                        move.pp,
                        move.priority,
                    )
                    for move in moves_by_id.values()
                ]
                await _write_batches(
                    connection,
                    MOVE_INSERT,
                    move_rows,
                    summary,
                    batch_size=CATALOG_BATCH_SIZE,
                )
                await _write_batches(
                    connection,
                    SPECIES_ABILITY_INSERT,
                    species_abilities.values(),
                    summary,
                    batch_size=RELATIONSHIP_BATCH_SIZE,
                )
                await _write_batches(
                    connection,
                    SPECIES_MOVE_INSERT,
                    species_moves.values(),
                    summary,
                    batch_size=RELATIONSHIP_BATCH_SIZE,
                )
        if summary["species"] % PROGRESS_INTERVAL or dry_run:
            _print_progress(summary)
    finally:
        await close_pool()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize local Gen 9 Showdown loadout data into PostgreSQL."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and count catalog entries without writing database rows.",
    )
    args = parser.parse_args()
    print(asyncio.run(sync_catalog(dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
