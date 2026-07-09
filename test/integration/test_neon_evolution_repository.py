import pytest

from core.candy.candy_type import CandyType
from infrastructure.evolution.neon_evolution_repository import (
    NeonEvolutionRepository,
)


@pytest.mark.asyncio
async def test_neon_evolution_repository_returns_bulbasaur_evolution():

    repository = NeonEvolutionRepository()

    rule = await repository.find_next(
        1,
    )

    assert rule is not None

    assert rule.from_species_id == 1

    assert rule.to_species_id == 2

    assert rule.candy_type == CandyType.GRASS

    assert rule.tier == "basic"
