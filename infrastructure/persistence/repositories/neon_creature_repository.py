from core.creature.creature import Creature
from core.creature.creature_mapper import CreatureMapper
from core.creature.creature_repository import CreatureRepository
from core.species.species_repository import SpeciesRepository
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

    async def save(
        self,
        creature: Creature,
    ) -> Creature:

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
                        speed_iv
                    )
                    VALUES (
                        $1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12, $13, $14
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

    async def update(
        self,
        creature: Creature,
    ) -> Creature:

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
                    size = $5,
                    hp_iv = $6,
                    attack_iv = $7,
                    defense_iv = $8,
                    special_attack_iv = $9,
                    special_defense_iv = $10,
                    speed_iv = $11
                WHERE id = $12
                RETURNING id
                """,
                params[1],  # species_id
                params[2],  # current_form_id
                params[3],  # is_shiny
                params[4],  # nature
                params[5],  # size
                params[6],  # hp_iv
                params[7],  # attack_iv
                params[8],  # defense_iv
                params[9],  # special_attack_iv
                params[10],  # special_defense_iv
                params[11],  # speed_iv
                creature.id,
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
