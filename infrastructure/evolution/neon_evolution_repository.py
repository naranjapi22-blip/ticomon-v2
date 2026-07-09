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

    async def find_options(
        self,
        species_id: int,
    ) -> list[EvolutionRule]:

        pool = await get_pool()

        async with pool.acquire() as connection:

            rows = await connection.fetch(
                """
                SELECT *
                FROM pokemon_evolutions
                WHERE from_species_id = $1
                ORDER BY id
                """,
                species_id,
            )

        return [self._mapper.from_row(row) for row in rows]
