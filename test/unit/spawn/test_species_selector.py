import pytest

from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.spawn_rarity import SpawnRarity
from core.spawn.species_selector import SpeciesSelector
from core.spawn.world import World
from test.factories import create_species
from test.unit.spawn.fakes import (
    FakeRaritySelector,
    FakeRuleEngine,
    FakeSpeciesRepository,
    FakeWeightedSelector,
)


@pytest.mark.asyncio
async def test_returns_requested_number_of_species():

    species = (
        create_species(id=1),
        create_species(id=2, name="Charmander"),
        create_species(id=3, name="Bulbasaur"),
    )

    selector = SpeciesSelector(
        repository=FakeSpeciesRepository(species),
        rarity_selector=FakeRaritySelector(SpawnRarity.COMMON),
        rule_engine=FakeRuleEngine(),
        weighted_selector=FakeWeightedSelector(),
    )

    profile = SpawnProfile(
        opportunity_count=3,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    result = await selector.select(
        context=context,
        profile=profile,
    )

    assert len(result) == 3


@pytest.mark.asyncio
async def test_never_returns_duplicate_species():

    species = (
        create_species(id=1),
        create_species(id=2, name="Charmander"),
        create_species(id=3, name="Bulbasaur"),
    )

    selector = SpeciesSelector(
        repository=FakeSpeciesRepository(species),
        rarity_selector=FakeRaritySelector(SpawnRarity.COMMON),
        rule_engine=FakeRuleEngine(),
        weighted_selector=FakeWeightedSelector(),
    )

    profile = SpawnProfile(
        opportunity_count=3,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    result = await selector.select(
        context=context,
        profile=profile,
    )

    ids = [pokemon.id for pokemon in result]

    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_repository_receives_selected_rarity():

    species = (create_species(id=1),)

    repository = FakeSpeciesRepository(species)

    rarity = SpawnRarity.EPIC

    selector = SpeciesSelector(
        repository=repository,
        rarity_selector=FakeRaritySelector(rarity),
        rule_engine=FakeRuleEngine(),
        weighted_selector=FakeWeightedSelector(),
    )

    profile = SpawnProfile(
        opportunity_count=1,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    await selector.select(
        context=context,
        profile=profile,
    )

    assert repository.last_requested_rarity == rarity


@pytest.mark.asyncio
async def test_rule_engine_is_used():

    species = (create_species(id=1),)

    engine = FakeRuleEngine()

    selector = SpeciesSelector(
        repository=FakeSpeciesRepository(species),
        rarity_selector=FakeRaritySelector(SpawnRarity.COMMON),
        rule_engine=engine,
        weighted_selector=FakeWeightedSelector(),
    )

    profile = SpawnProfile(
        opportunity_count=1,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    await selector.select(
        context=context,
        profile=profile,
    )

    assert engine.calls == 1


@pytest.mark.asyncio
async def test_weighted_selector_is_used():

    species = (create_species(id=1),)

    weighted = FakeWeightedSelector()

    selector = SpeciesSelector(
        repository=FakeSpeciesRepository(species),
        rarity_selector=FakeRaritySelector(SpawnRarity.COMMON),
        rule_engine=FakeRuleEngine(),
        weighted_selector=weighted,
    )

    profile = SpawnProfile(
        opportunity_count=1,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    await selector.select(
        context=context,
        profile=profile,
    )

    assert weighted.calls == 1
