from __future__ import annotations

from contextlib import asynccontextmanager

from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.creature.creature_mapper import CreatureMapper
from core.release.release_unit_of_work import ReleaseTransaction, ReleaseUnitOfWork
from core.species.species_mapper import SpeciesMapper
from core.species.variant import Variant
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import CandyMapper
from infrastructure.species.evolution_chain_loader import build_evolution_chains


class NeonReleaseUnitOfWork(ReleaseUnitOfWork):
    @asynccontextmanager
    async def transaction(self):
        pool = await get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                yield _NeonReleaseTransaction(connection)


class _NeonReleaseTransaction(ReleaseTransaction):
    def __init__(self, connection) -> None:
        self._connection = connection
        self._creature_mapper = CreatureMapper()
        self._species_mapper = SpeciesMapper()
        self._candy_mapper = CandyMapper()

    async def get_creatures_by_collection_numbers(
        self,
        trainer_id: int,
        collection_numbers: list[int] | tuple[int, ...],
    ) -> list[Creature]:
        requested = list(collection_numbers)
        if not requested:
            return []

        rows = await self._connection.fetch(
            """
            SELECT c.*, sv.id AS variant_id, sv.name AS variant_name
            FROM creatures c
            LEFT JOIN species_variants sv ON sv.id = c.current_form_id
            WHERE c.trainer_id = $1
              AND c.collection_number = ANY($2::integer[])
            ORDER BY c.collection_number
            FOR UPDATE OF c
            """,
            trainer_id,
            requested,
        )
        rows_by_number = {row["collection_number"]: row for row in rows}
        for collection_number in requested:
            if collection_number not in rows_by_number:
                raise ValueError(f"Creature #{collection_number} was not found.")

        species_ids = sorted({row["species_id"] for row in rows})
        species_rows = await self._connection.fetch(
            """
            SELECT *
            FROM species
            WHERE id = ANY($1::bigint[])
            ORDER BY id
            """,
            species_ids,
        )
        variant_rows = await self._connection.fetch(
            """
            SELECT species_id, id, name
            FROM species_variants
            WHERE species_id = ANY($1::bigint[])
            ORDER BY species_id, id
            """,
            species_ids,
        )
        evolution_rows = await self._connection.fetch(
            "SELECT from_species_id, to_species_id, tier FROM pokemon_evolutions"
        )
        evolution_chains = build_evolution_chains(evolution_rows)
        variants_by_species: dict[int, list] = {}
        for row in variant_rows:
            variants_by_species.setdefault(row["species_id"], []).append(
                Variant(id=row["id"], name=row["name"])
            )
        species_by_id = {
            row["id"]: self._species_mapper.from_row(
                row,
                tuple(variants_by_species.get(row["id"], ())),
                evolution_chains.get(row["id"]),
            )
            for row in species_rows
        }
        for row in rows:
            species_id = row["species_id"]
            if species_id not in species_by_id:
                raise ValueError(f"Species with id {species_id} was not found.")

        return [
            self._creature_mapper.from_row(
                row=rows_by_number[number],
                species=species_by_id[rows_by_number[number]["species_id"]],
            )
            for number in requested
        ]

    async def get_candy_inventory(self, trainer_id: int) -> CandyInventory:
        rows = await self._connection.fetch(
            """
            SELECT candy_type, amount
            FROM trainer_candies
            WHERE trainer_id = $1
            FOR UPDATE
            """,
            trainer_id,
        )
        return self._candy_mapper.from_rows(rows)

    async def get_assigned_creature_ids(
        self,
        trainer_id: int,
        creature_ids: list[int] | tuple[int, ...],
    ) -> set[int]:
        if not creature_ids:
            return set()

        rows = await self._connection.fetch(
            """
            SELECT creature_id
            FROM trainer_team_slots
            WHERE trainer_id = $1
              AND creature_id = ANY($2::bigint[])
            FOR UPDATE
            """,
            trainer_id,
            list(creature_ids),
        )
        return {row["creature_id"] for row in rows}

    async def delete_creatures(
        self,
        trainer_id: int,
        creatures: list[Creature] | tuple[Creature, ...],
    ) -> None:
        creature_ids = [creature.id for creature in creatures]
        if not creature_ids:
            return

        result = await self._connection.execute(
            """
            DELETE FROM creatures
            WHERE trainer_id = $1
              AND id = ANY($2::bigint[])
            """,
            trainer_id,
            creature_ids,
        )
        if result != f"DELETE {len(creature_ids)}":
            raise ValueError("One or more creatures could not be released.")

    async def save_candy_inventory(
        self,
        trainer_id: int,
        inventory: CandyInventory,
    ) -> None:
        await self._connection.execute(
            "DELETE FROM trainer_candies WHERE trainer_id = $1",
            trainer_id,
        )
        rows = self._candy_mapper.to_rows(inventory)
        if rows:
            await self._connection.executemany(
                """
                INSERT INTO trainer_candies (trainer_id, candy_type, amount)
                VALUES ($1, $2, $3)
                """,
                [(trainer_id, candy_type.value, amount) for candy_type, amount in rows],
            )
