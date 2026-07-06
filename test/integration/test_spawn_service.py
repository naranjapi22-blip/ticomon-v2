import pytest

from core.spawn.spawn_service import SpawnService
from infrastructure.species.neon_species_repository import NeonSpeciesRepository


@pytest.mark.asyncio
async def test_spawn_from_db():
    repository = NeonSpeciesRepository()
    service = SpawnService(repository)

    opportunity = await service.spawn()

    assert opportunity is not None
    assert opportunity.species is not None
    assert opportunity.species.name is not None
    assert isinstance(opportunity.species.types, list)
