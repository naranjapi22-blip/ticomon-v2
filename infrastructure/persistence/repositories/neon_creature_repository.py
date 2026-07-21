from core.creature.creature import Creature
from core.creature.creature_mapper import CreatureMapper
from core.creature.creature_repository import CreatureRepository
from core.species.species_repository import SpeciesRepository
from infrastructure.battle.poke_env.loadout_catalog import PokeEnvLoadoutCatalog
from infrastructure.db_config import get_pool


class NeonCreatureRepository(CreatureRepository):
    """
    PostgreSQL implementation of CreatureRepository backed by Neon.
    """

    def __init__(
        self,
        species_repository: SpeciesRepository,
    ) -> None:
        self._mapper = CreatureMapper()
        self._species_repository = species_repository
        self._loadout_catalog = PokeEnvLoadoutCatalog()

    def _ensure_loadout(self, creature: Creature) -> Creature:
        abilities = self._loadout_catalog.abilities_for(creature.species)
        if not abilities and not creature.ability_id:
            raise ValueError(
                f"No ability catalog is available for species {creature.species.id}."
            )
        ability_id = creature.ability_id
        valid_abilities = {ability.id for ability in abilities}
        if ability_id not in valid_abilities:
            ability_id = abilities[0].id if abilities else None
        moves = creature.moves or self._loadout_catalog.initial_moves(
            creature.species,
            seed=creature.id or creature.collection_number or creature.species.id,
        )
        return CreatureMapper.from_row(
            {
                "id": creature.id,
                "collection_number": creature.collection_number,
                "trainer_id": creature.trainer_id,
                "original_trainer_id": creature.original_trainer_id,
                "hp_iv": creature.ivs.hp,
                "attack_iv": creature.ivs.attack,
                "defense_iv": creature.ivs.defense,
                "special_attack_iv": creature.ivs.special_attack,
                "special_defense_iv": creature.ivs.special_defense,
                "speed_iv": creature.ivs.speed,
                "size": creature.size.value,
                "nature": creature.nature.name,
                "minted_nature": (
                    creature.minted_nature.name if creature.minted_nature else None
                ),
                "is_shiny": creature.is_shiny,
                "variant_id": (
                    creature.current_form.id if creature.current_form else None
                ),
                "variant_name": (
                    creature.current_form.name if creature.current_form else None
                ),
                "ability_id": ability_id,
                "equipped_moves": moves,
            },
            creature.species,
        )

    async def save(
        self,
        creature: Creature,
    ) -> Creature:

        creature = self._ensure_loadout(creature)

        pool = await get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock($1)",
                    creature.trainer_id,
                )

                collection_number = await connection.fetchval(
                    """
                    SELECT COALESCE(MAX(collection_number), 0) + 1
                    FROM creatures
                    WHERE trainer_id = $1
                    """,
                    creature.trainer_id,
                )

                params = self._mapper.to_row(creature)

                created = await connection.fetchrow(
                    """
                    INSERT INTO creatures (
                        trainer_id,
                        original_trainer_id,
                        collection_number,
                        species_id,
                        current_form_id,
                        is_shiny,
                        nature,
                        size,
                        hp_iv,
                        attack_iv,
                        defense_iv,
                        special_attack_iv,
                        special_defense_iv,
                        speed_iv,
                        minted_nature
                        , ability_id, equipped_moves
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
                    )
                    RETURNING id
                    """,
                    params[0],  # trainer_id
                    params[1],  # original_trainer_id
                    collection_number,
                    *params[2:],
                )

                row = await connection.fetchrow(
                    """
                    SELECT
                        c.*,
                        sv.id AS variant_id,
                        sv.name AS variant_name
                    FROM creatures c
                    LEFT JOIN species_variants sv
                        ON sv.id = c.current_form_id
                    WHERE c.id = $1
                    """,
                    created["id"],
                )

            species = await self._species_repository.get(
                row["species_id"],
            )

            return self._mapper.from_row(
                row=row,
                species=species,
            )

    async def get(
        self,
        creature_id: int,
    ) -> Creature:
        """
        Returns a Creature by its identifier.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT
                    c.*,
                    sv.id AS variant_id,
                    sv.name AS variant_name
                FROM creatures c
                LEFT JOIN species_variants sv
                    ON sv.id = c.current_form_id
                WHERE c.id = $1
                """,
                creature_id,
            )
        if row is None:
            raise ValueError(f"Creature with id {creature_id} was not found.")

        species = await self._species_repository.get(
            row["species_id"],
        )

        return self._mapper.from_row(
            row=row,
            species=species,
        )

    async def get_many(
        self,
        creature_ids: list[int] | tuple[int, ...],
    ) -> list[Creature]:
        """
        Returns all creatures matching the given identifiers.
        """

        if not creature_ids:
            return []

        pool = await get_pool()

        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT
                    c.*,
                    sv.id AS variant_id,
                    sv.name AS variant_name
                FROM creatures c
                LEFT JOIN species_variants sv
                    ON sv.id = c.current_form_id
                WHERE c.id = ANY($1::bigint[])
                ORDER BY c.id
                """,
                list(creature_ids),
            )

        species_ids = list(
            dict.fromkeys(row["species_id"] for row in rows),
        )
        species_list = await self._species_repository.get_many(
            species_ids,
        )
        species_by_id = {species.id: species for species in species_list}

        creatures: list[Creature] = []

        for row in rows:
            species = species_by_id[row["species_id"]]
            creatures.append(
                self._mapper.from_row(
                    row=row,
                    species=species,
                )
            )

        return creatures

    async def has_species(
        self,
        trainer_id: int,
        species_id: int,
    ) -> bool:
        """
        Returns whether the trainer has already captured the species.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            return await connection.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM creatures
                    WHERE trainer_id = $1
                      AND species_id = $2
                )
                """,
                trainer_id,
                species_id,
            )

    async def count_creatures(
        self,
        trainer_id: int,
    ) -> int:
        """
        Returns the total number of creatures owned by the trainer.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            return await connection.fetchval(
                """
                SELECT COUNT(*)
                FROM creatures
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

    async def count_species(
        self,
        trainer_id: int,
    ) -> int:
        """
        Returns the number of unique species owned by the trainer.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            return await connection.fetchval(
                """
                SELECT COUNT(DISTINCT species_id)
                FROM creatures
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

    async def count_shinies(
        self,
        trainer_id: int,
    ) -> int:
        """
        Returns the number of shiny creatures owned by the trainer.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            return await connection.fetchval(
                """
                SELECT COUNT(*)
                FROM creatures
                WHERE trainer_id = $1
                  AND is_shiny = TRUE
                """,
                trainer_id,
            )

    async def get_by_collection_number(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> Creature:
        """
        Returns a trainer's creature by its collection number.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT
                    c.*,
                    sv.id AS variant_id,
                    sv.name AS variant_name
                FROM creatures c
                LEFT JOIN species_variants sv
                    ON sv.id = c.current_form_id
                WHERE c.trainer_id = $1
                AND c.collection_number = $2
                """,
                trainer_id,
                collection_number,
            )

        if row is None:
            raise ValueError(f"Creature #{collection_number} was not found.")

        species = await self._species_repository.get(
            row["species_id"],
        )

        return self._mapper.from_row(
            row=row,
            species=species,
        )

    async def get_by_collection_numbers(
        self,
        trainer_id: int,
        collection_numbers: list[int] | tuple[int, ...],
    ) -> list[Creature]:
        requested = list(collection_numbers)
        if not requested:
            return []

        pool = await get_pool()
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT
                    c.*,
                    sv.id AS variant_id,
                    sv.name AS variant_name
                FROM creatures c
                LEFT JOIN species_variants sv
                    ON sv.id = c.current_form_id
                WHERE c.trainer_id = $1
                  AND c.collection_number = ANY($2::integer[])
                ORDER BY c.collection_number
                """,
                trainer_id,
                requested,
            )

        rows_by_number = {row["collection_number"]: row for row in rows}
        for collection_number in requested:
            if collection_number not in rows_by_number:
                raise ValueError(f"Creature #{collection_number} was not found.")

        species_by_id = {
            species.id: species
            for species in await self._species_repository.get_many(
                list({row["species_id"] for row in rows})
            )
        }
        return [
            self._mapper.from_row(
                row=rows_by_number[number],
                species=species_by_id[rows_by_number[number]["species_id"]],
            )
            for number in requested
        ]

    async def get_by_species(
        self,
        trainer_id: int,
        species_id: int,
    ) -> list[Creature]:
        """
        Returns every creature of the given species owned by the trainer.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT
                    c.*,
                    sv.id AS variant_id,
                    sv.name AS variant_name
                FROM creatures c
                LEFT JOIN species_variants sv
                    ON sv.id = c.current_form_id
                WHERE c.trainer_id = $1
                AND c.species_id = $2
                ORDER BY c.collection_number
                """,
                trainer_id,
                species_id,
            )

        creatures: list[Creature] = []

        for row in rows:
            species = await self._species_repository.get(
                row["species_id"],
            )

            creatures.append(
                self._mapper.from_row(
                    row=row,
                    species=species,
                )
            )

        return creatures

    async def get_by_trainer(
        self,
        trainer_id: int,
    ) -> list[Creature]:
        """
        Returns every creature owned by the trainer.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT
                    c.*,
                    sv.id AS variant_id,
                    sv.name AS variant_name
                FROM creatures c
                LEFT JOIN species_variants sv
                    ON sv.id = c.current_form_id
                WHERE c.trainer_id = $1
                ORDER BY c.collection_number
                """,
                trainer_id,
            )

        creatures: list[Creature] = []

        species_ids = list(
            dict.fromkeys(row["species_id"] for row in rows),
        )

        species_list = await self._species_repository.get_many(
            species_ids,
        )

        species_by_id = {species.id: species for species in species_list}

        for row in rows:
            species = species_by_id[row["species_id"]]

            creatures.append(
                self._mapper.from_row(
                    row=row,
                    species=species,
                )
            )

        return creatures

    async def get_duplicate_species(
        self,
        trainer_id: int,
    ) -> list[tuple[int, int]]:
        """
        Returns species ids with more than one owned creature.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT
                    species_id,
                    COUNT(*) AS amount
                FROM creatures
                WHERE trainer_id = $1
                GROUP BY species_id
                HAVING COUNT(*) > 1
                ORDER BY amount DESC
                """,
                trainer_id,
            )

        return [
            (
                row["species_id"],
                row["amount"],
            )
            for row in rows
        ]

    async def get_discovered_species(
        self,
        trainer_id: int,
    ) -> set[int]:
        """
        Returns the ids of every discovered species.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT DISTINCT species_id
                FROM creatures
                WHERE trainer_id = $1
                """,
                trainer_id,
            )

        return {row["species_id"] for row in rows}

    async def get_legal_moves(self, species_id: int):
        """Returns the persisted species_moves catalog in one query."""
        from core.creature.move import CreatureMove, canonicalize_move_id

        pool = await get_pool()
        async with pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT m.id, m.display_name, m.type, m.category, m.power,
                       m.accuracy, m.pp, m.priority
                FROM species_moves sm
                JOIN moves m ON m.id = sm.move_id
                WHERE sm.species_id = $1
                ORDER BY m.display_name
                """,
                species_id,
            )
        return tuple(
            CreatureMove(
                id=canonicalize_move_id(row["id"]),
                display_name=row["display_name"],
                move_type=row["type"],
                category=row["category"],
                base_power=row["power"],
                accuracy=row["accuracy"],
                pp=row["pp"],
                priority=row["priority"],
            )
            for row in rows
        )

    async def update_moves(
        self,
        *,
        trainer_id: int,
        collection_number: int,
        moves: tuple[str, ...],
        ability_id: str | None,
    ) -> Creature:
        """Atomically replaces only equipped_moves and preserves ability_id."""
        pool = await get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                updated = await connection.fetchrow(
                    """
                    UPDATE creatures c
                    SET equipped_moves = $3::text[]
                    WHERE c.trainer_id = $1
                      AND c.collection_number = $2
                      AND c.ability_id IS NOT DISTINCT FROM $4
                      AND cardinality($3::text[]) BETWEEN 1 AND 4
                      AND cardinality($3::text[]) = (
                          SELECT count(DISTINCT requested.move_id)
                          FROM unnest($3::text[]) requested(move_id)
                      )
                      AND NOT EXISTS (
                          SELECT 1
                          FROM unnest($3::text[]) requested(move_id)
                          WHERE NOT EXISTS (
                              SELECT 1 FROM species_moves sm
                              WHERE sm.species_id = c.species_id
                                AND sm.move_id = requested.move_id
                          )
                      )
                    RETURNING c.id
                    """,
                    trainer_id,
                    collection_number,
                    list(moves),
                    ability_id,
                )
                if updated is None:
                    raise ValueError("The creature loadout could not be updated.")
                row = await connection.fetchrow(
                    """
                    SELECT c.*, sv.id AS variant_id, sv.name AS variant_name
                    FROM creatures c
                    LEFT JOIN species_variants sv ON sv.id = c.current_form_id
                    WHERE c.id = $1
                    """,
                    updated["id"],
                )
        species = await self._species_repository.get(row["species_id"])
        return self._mapper.from_row(row, species)

    async def update(
        self,
        creature: Creature,
    ) -> Creature:

        creature = self._ensure_loadout(creature)

        pool = await get_pool()

        async with pool.acquire() as connection:

            params = self._mapper.to_row(
                creature,
            )

            updated = await connection.fetchrow(
                """
                UPDATE creatures
                SET
                    species_id = $1,
                    current_form_id = $2,
                    is_shiny = $3,
                    nature = $4,
                    minted_nature = $5,
                    size = $6,
                    hp_iv = $7,
                    attack_iv = $8,
                    defense_iv = $9,
                    special_attack_iv = $10,
                    special_defense_iv = $11,
                        speed_iv = $12
                        , ability_id = $14, equipped_moves = $15
                WHERE id = $13
                RETURNING id
                """,
                params[2],  # species_id
                params[3],  # current_form_id
                params[4],  # is_shiny
                params[5],  # nature
                params[13],  # minted_nature
                params[6],  # size
                params[7],  # hp_iv
                params[8],  # attack_iv
                params[9],  # defense_iv
                params[10],  # special_attack_iv
                params[11],  # special_defense_iv
                params[12],  # speed_iv
                creature.id,
                params[14],
                params[15],
            )

            if updated is None:
                raise ValueError(f"Creature with id {creature.id} was not found.")

            row = await connection.fetchrow(
                """
                SELECT
                    c.*,
                    sv.id AS variant_id,
                    sv.name AS variant_name
                FROM creatures c
                LEFT JOIN species_variants sv
                    ON sv.id = c.current_form_id
                WHERE c.id = $1
                """,
                updated["id"],
            )

            species = await self._species_repository.get(
                row["species_id"],
            )

            return self._mapper.from_row(
                row=row,
                species=species,
            )

    async def delete(
        self,
        creature: Creature,
    ) -> None:

        pool = await get_pool()

        async with pool.acquire() as connection:

            await connection.execute(
                """
                DELETE
                FROM creatures
                WHERE id = $1
                """,
                creature.id,
            )

    async def delete_many(
        self,
        trainer_id: int,
        creatures: list[Creature] | tuple[Creature, ...],
    ) -> None:
        creature_ids = [creature.id for creature in creatures]
        if not creature_ids:
            return

        pool = await get_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                result = await connection.execute(
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


async def _fetch_creature(
    self,
    connection,
    query: str,
    *args,
):
    return await connection.fetchrow(
        f"""
        SELECT
            c.*,
            sv.id AS variant_id,
            sv.name AS variant_name
        FROM (
            {query}
        ) c
        LEFT JOIN species_variants sv
            ON sv.id = c.current_form_id
        """,
        *args,
    )
