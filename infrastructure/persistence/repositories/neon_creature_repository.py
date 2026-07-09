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

            collection_number = await connection.fetchval(
                """
                SELECT COALESCE(MAX(collection_number), 0) + 1
                FROM creatures
                WHERE trainer_id = $1
                """,
                creature.trainer_id,
            )

            params = self._mapper.to_row(creature)

            row = await connection.fetchrow(
                """
                INSERT INTO creatures (
                    trainer_id,
                    collection_number,
                    species_id,
                    variant,
                    is_shiny,
                    nature,
                    size,
                    hp_iv,
                    attack_iv,
                    defense_iv,
                    special_attack_iv,
                    special_defense_iv,
                    speed_iv,
                    current_form
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    $8, $9, $10, $11, $12, $13, $14
                )
                RETURNING *
                """,
                params[0],  # trainer_id
                collection_number,
                *params[1:],
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
                SELECT *
                FROM creatures
                WHERE id = $1
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
                SELECT *
                FROM creatures
                WHERE trainer_id = $1
                  AND collection_number = $2
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
                SELECT *
                FROM creatures
                WHERE trainer_id = $1
                  AND species_id = $2
                ORDER BY collection_number
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

            row = await connection.fetchrow(
                """
                UPDATE creatures
                SET
                    species_id = $1,
                    variant = $2,
                    is_shiny = $3,
                    nature = $4,
                    size = $5,
                    hp_iv = $6,
                    attack_iv = $7,
                    defense_iv = $8,
                    special_attack_iv = $9,
                    special_defense_iv = $10,
                    speed_iv = $11,
                    current_form = $12
                WHERE id = $13
                RETURNING *
                """,
                params[1],  # species_id
                params[2],  # variant
                params[3],  # is_shiny
                params[4],  # nature
                params[5],  # size
                params[6],  # hp_iv
                params[7],  # attack_iv
                params[8],  # defense_iv
                params[9],  # special_attack_iv
                params[10],  # special_defense_iv
                params[11],  # speed_iv
                params[12],  # current_form
                creature.id,
            )

        if row is None:
            raise ValueError(f"Creature with id {creature.id} was not found.")

        species = await self._species_repository.get(
            row["species_id"],
        )

        return self._mapper.from_row(
            row=row,
            species=species,
        )
