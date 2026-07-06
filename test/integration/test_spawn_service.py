import pytest

from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.spawn_factory import SpawnFactory
from core.spawn.world import World
from infrastructure.species.neon_species_repository import NeonSpeciesRepository


@pytest.mark.asyncio
async def test_spawn_from_db():
    repository = NeonSpeciesRepository()
    service = SpawnFactory.create(repository)

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    profile = SpawnProfile(
        opportunity_count=1,
    )

    opportunities = await service.spawn(
        context=context,
        profile=profile,
    )

    assert len(opportunities) == 1

    opportunity = opportunities[0]

    assert opportunity.species is not None
    assert opportunity.species.name is not None
    assert isinstance(opportunity.species.types, list)
