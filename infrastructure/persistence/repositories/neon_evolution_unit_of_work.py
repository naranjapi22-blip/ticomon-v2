from __future__ import annotations

from contextlib import asynccontextmanager

from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.creature.creature_mapper import CreatureMapper
from core.evolution.evolution_unit_of_work import (
    EvolutionTransaction,
    EvolutionUnitOfWork,
)
from core.species.species_mapper import SpeciesMapper
from core.species.variant import Variant
from infrastructure.battle.poke_env.loadout_catalog import PokeEnvLoadoutCatalog
from infrastructure.db_config import get_pool
from infrastructure.persistence.mappers.candy_mapper import CandyMapper


class NeonEvolutionUnitOfWork(EvolutionUnitOfWork):
    @asynccontextmanager
    async def transaction(self):
        pool = await get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                yield _NeonEvolutionTransaction(connection)


class _NeonEvolutionTransaction(EvolutionTransaction):
    def __init__(self, connection) -> None:
        self._connection = connection
        self._creature_mapper = CreatureMapper()
        self._species_mapper = SpeciesMapper()
        self._candy_mapper = CandyMapper()
        self._loadout_catalog = PokeEnvLoadoutCatalog()

    async def get_creature(self, trainer_id: int, collection_number: int) -> Creature:
        row = await self._connection.fetchrow(
            """
            SELECT c.*, sv.id AS variant_id, sv.name AS variant_name
            FROM creatures c
            LEFT JOIN species_variants sv ON sv.id = c.current_form_id
            WHERE c.trainer_id = $1 AND c.collection_number = $2
            FOR UPDATE OF c
            """,
            trainer_id,
            collection_number,
        )
        if row is None:
            raise ValueError(f"Creature #{collection_number} was not found.")
        species = await self._load_species(row["species_id"])
        return self._creature_mapper.from_row(row, species)

    async def _load_species(self, species_id: int):
        row = await self._connection.fetchrow(
            "SELECT * FROM species WHERE id = $1", species_id
        )
        if row is None:
            raise ValueError(f"Species with id {species_id} was not found.")
        variants = await self._connection.fetch(
            """
            SELECT id, name FROM species_variants
            WHERE species_id = $1 ORDER BY id
            """,
            species_id,
        )
        return self._species_mapper.from_row(
            row, tuple(Variant(id=item["id"], name=item["name"]) for item in variants)
        )

    async def get_candy_inventory(self, trainer_id: int) -> CandyInventory:
        rows = await self._connection.fetch(
            """
            SELECT candy_type, amount FROM trainer_candies
            WHERE trainer_id = $1 FOR UPDATE
            """,
            trainer_id,
        )
        return self._candy_mapper.from_rows(rows)

    async def update_creature(self, creature: Creature) -> Creature:
        ability_id, moves = self._loadout_catalog.normalize_loadout(creature)
        params = self._creature_mapper.to_row(creature)
        updated = await self._connection.fetchrow(
            """
            UPDATE creatures
            SET species_id = $1, current_form_id = $2, is_shiny = $3,
                nature = $4, minted_nature = $5, size = $6,
                hp_iv = $7, attack_iv = $8, defense_iv = $9,
                special_attack_iv = $10, special_defense_iv = $11,
                speed_iv = $12, ability_id = $14, equipped_moves = $15
            WHERE id = $13
            RETURNING id
            """,
            params[2],
            params[3],
            params[4],
            params[5],
            params[13],
            params[6],
            params[7],
            params[8],
            params[9],
            params[10],
            params[11],
            params[12],
            creature.id,
            ability_id,
            list(moves),
        )
        if updated is None:
            raise ValueError(f"Creature with id {creature.id} was not found.")
        row = await self._connection.fetchrow(
            """
            SELECT c.*, sv.id AS variant_id, sv.name AS variant_name
            FROM creatures c
            LEFT JOIN species_variants sv ON sv.id = c.current_form_id
            WHERE c.id = $1
            """,
            updated["id"],
        )
        species = await self._load_species(row["species_id"])
        return self._creature_mapper.from_row(row, species)

    async def save_candy_inventory(
        self, trainer_id: int, inventory: CandyInventory
    ) -> None:
        await self._connection.execute(
            "DELETE FROM trainer_candies WHERE trainer_id = $1", trainer_id
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
