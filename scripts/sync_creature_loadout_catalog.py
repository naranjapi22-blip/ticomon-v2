"""Synchronize Gen 9 Showdown abilities and learnsets into PostgreSQL."""

import argparse
import asyncio
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
    }
    try:
        species = await species_repository.get_all()
        if dry_run:
            for item in species:
                abilities = catalog.abilities_for(item)
                moves = catalog.moves_for(item)
                summary["species"] += 1
                summary["abilities"] += len(abilities)
                summary["moves"] += len(moves)
                summary["species_without_abilities"] += not bool(abilities)
                summary["species_without_moves"] += not bool(moves)
            return summary
        async with pool.acquire() as connection:
            async with connection.transaction():
                for item in species:
                    summary["species"] += 1
                    abilities = catalog.abilities_for(item)
                    moves = catalog.moves_for(item)
                    summary["abilities"] += len(abilities)
                    summary["moves"] += len(moves)
                    summary["species_without_abilities"] += not bool(abilities)
                    summary["species_without_moves"] += not bool(moves)
                    for ability in abilities:
                        await connection.execute(
                            """
                            INSERT INTO abilities (id, canonical_name, display_name)
                            VALUES ($1, $1, $2)
                            ON CONFLICT (id) DO UPDATE SET
                                display_name = EXCLUDED.display_name
                            """,
                            ability.id,
                            ability.display_name,
                        )
                        await connection.execute(
                            """
                            INSERT INTO species_abilities
                                (species_id, ability_id, slot, is_hidden)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (species_id, ability_id) DO UPDATE
                            SET slot = EXCLUDED.slot, is_hidden = EXCLUDED.is_hidden
                            """,
                            item.id,
                            ability.id,
                            ability.slot,
                            ability.is_hidden,
                        )
                    for move in moves:
                        await connection.execute(
                            """
                            INSERT INTO moves
                                (id, canonical_name, display_name, type, category,
                                 power, accuracy, pp, priority)
                            VALUES ($1, $1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (id) DO UPDATE SET
                                display_name = EXCLUDED.display_name,
                                type = EXCLUDED.type, category = EXCLUDED.category,
                                power = EXCLUDED.power, accuracy = EXCLUDED.accuracy,
                                pp = EXCLUDED.pp, priority = EXCLUDED.priority
                            """,
                            move.id,
                            move.display_name,
                            move.move_type,
                            move.category,
                            move.base_power,
                            move.accuracy,
                            move.pp,
                            move.priority,
                        )
                        await connection.execute(
                            """
                            INSERT INTO species_moves (species_id, move_id, generation)
                            VALUES ($1, $2, 9)
                            ON CONFLICT (species_id, move_id) DO NOTHING
                            """,
                            item.id,
                            move.id,
                        )
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
