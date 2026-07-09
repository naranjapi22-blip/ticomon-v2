from core.evolution.evolution_repository import EvolutionRepository
from core.evolution.evolution_rule import EvolutionRule
from infrastructure.db_config import get_pool
from infrastructure.evolution.evolution_mapper import EvolutionMapper


class NeonEvolutionRepository(EvolutionRepository):
    """
    PostgreSQL implementation of EvolutionRepository backed by Neon.
    """

    def __init__(self) -> None:
        self._mapper = EvolutionMapper()

    async def find_next(
        self,
        species_id: int,
    ) -> EvolutionRule | None:
        """
        Returns the evolution rule for a species.
        """

        pool = await get_pool()

        async with pool.acquire() as connection:

            row = await connection.fetchrow(
                """
                SELECT *
                FROM pokemon_evolutions
                WHERE from_species_id = $1
                LIMIT 1
                """,
                species_id,
            )

        if row is None:
            return None

        return self._mapper.from_row(row)
