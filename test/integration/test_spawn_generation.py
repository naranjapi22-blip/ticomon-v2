import pytest

from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.spawn_factory import SpawnFactory
from core.spawn.world import World
from infrastructure.species.neon_species_repository import NeonSpeciesRepository


@pytest.mark.asyncio
async def test_spawn_generates_opportunities():
    repository = NeonSpeciesRepository()

    service = SpawnFactory.create(repository)

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
        event=None,
    )

    profile = SpawnProfile(
        opportunity_count=3,
    )

    opportunities = await service.spawn(
        context=context,
        profile=profile,
    )

    assert len(opportunities) == 3

    for opportunity in opportunities:
        assert opportunity.species is not None
        assert opportunity.ivs is not None
        assert opportunity.nature is not None
        assert opportunity.size is not None
