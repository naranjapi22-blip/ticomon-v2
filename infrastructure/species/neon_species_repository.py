from core.spawn.spawn_rarity import SpawnRarity
from core.species.species import Species
from core.species.species_mapper import SpeciesMapper
from core.species.species_repository import SpeciesRepository
from infrastructure.db_config import get_pool


class NeonSpeciesRepository(SpeciesRepository):
    """
    PostgreSQL implementation of SpeciesRepository backed by Neon.
    """

    def __init__(self) -> None:
        self._mapper = SpeciesMapper()

    async def get(
        self,
        species_id: int,
    ) -> Species:
        """
        Returns a species by its identifier.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT *
                FROM species
                WHERE id = $1
                """,
                species_id,
            )

        if row is None:
            raise ValueError(f"Species with id {species_id} was not found.")

        return self._mapper.from_row(row)

    async def find_by_name(
        self,
        name: str,
    ) -> Species | None:
        """
        Returns a species by its name.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT *
                FROM species
                WHERE name = $1
                """,
                name,
            )

        if row is None:
            return None

        return self._mapper.from_row(row)

    async def get_all(self) -> tuple[Species, ...]:
        """
        Returns all registered species ordered by identifier.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT *
                FROM species
                ORDER BY id
                """
            )

        return tuple(self._mapper.from_row(row) for row in rows)

    async def find_by_spawn_rarity(
        self,
        rarity: SpawnRarity,
    ) -> tuple[Species, ...]:
        """
        Returns all species belonging to the given spawn rarity.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT *
                FROM species
                WHERE spawn_rarity = $1
                ORDER BY id
                """,
                rarity.value,
            )

        return tuple(self._mapper.from_row(row) for row in rows)
