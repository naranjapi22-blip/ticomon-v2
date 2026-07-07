import pytest

from core.spawn.application.spawn_service import SpawnService
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.world import World
from test.factories import create_species


class FakeSpeciesSelector:
    def __init__(self, species):
        self._species = species
        self.calls = 0

    async def select(
        self,
        context,
        profile,
    ):
        self.calls += 1
        return self._species


@pytest.mark.asyncio
async def test_returns_opportunities_for_selected_species():

    species = (
        create_species(id=25, name="Pikachu"),
        create_species(id=4, name="Charmander"),
        create_species(id=7, name="Squirtle"),
    )

    selector = FakeSpeciesSelector(species)

    service = SpawnService(
        selector=selector,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    profile = SpawnProfile(
        opportunity_count=3,
    )

    result = await service.spawn(
        context=context,
        profile=profile,
    )

    assert len(result) == 3

    assert result[0].species == species[0]
    assert result[1].species == species[1]
    assert result[2].species == species[2]


@pytest.mark.asyncio
async def test_calls_species_selector_once():

    selector = FakeSpeciesSelector((create_species(id=25),))

    service = SpawnService(
        selector=selector,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    profile = SpawnProfile(
        opportunity_count=1,
    )

    await service.spawn(
        context=context,
        profile=profile,
    )

    assert selector.calls == 1


@pytest.mark.asyncio
async def test_returns_empty_tuple_when_selector_returns_no_species():

    selector = FakeSpeciesSelector(())

    service = SpawnService(
        selector=selector,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    profile = SpawnProfile(
        opportunity_count=0,
    )

    result = await service.spawn(
        context=context,
        profile=profile,
    )

    assert result == ()
