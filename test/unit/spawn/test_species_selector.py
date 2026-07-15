from dataclasses import replace

import pytest

from core.rarity import Rarity
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.species_selector import SpeciesSelector
from core.spawn.world import World
from core.species import is_regional_species
from test.factories import create_species
from test.unit.spawn.fakes import (
    FakeRaritySelector,
    FakeRuleEngine,
    FakeSpeciesRepository,
    FakeWeightedSelector,
)


def regional_species(*, id: int, pokeapi_id: int, name: str):
    return replace(
        create_species(id=id, name=name),
        pokeapi_id=pokeapi_id,
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
        rarity_selector=FakeRaritySelector(Rarity.COMMON),
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
        rarity_selector=FakeRaritySelector(Rarity.COMMON),
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
async def test_excludes_regional_forms_before_spawn_selection():

    regional_forms = (
        regional_species(id=10091, pokeapi_id=10091, name="Alolan Rattata"),
        regional_species(id=10161, pokeapi_id=10161, name="Galarian Meowth"),
        regional_species(id=10229, pokeapi_id=10229, name="Hisuian Growlithe"),
        regional_species(id=10250, pokeapi_id=10250, name="Paldean Wooper"),
    )
    ordinary_forms = (
        create_species(id=19, name="Rattata"),
        create_species(id=52, name="Meowth"),
        create_species(id=58, name="Growlithe"),
        create_species(id=194, name="Wooper"),
    )

    selector = SpeciesSelector(
        repository=FakeSpeciesRepository(regional_forms + ordinary_forms),
        rarity_selector=FakeRaritySelector(Rarity.COMMON),
        rule_engine=FakeRuleEngine(),
        weighted_selector=FakeWeightedSelector(),
    )

    result = await selector.select(
        context=SpawnContext(world=World.MAIN, region=Region.KANTO),
        profile=SpawnProfile(opportunity_count=len(ordinary_forms)),
    )

    assert len(result) == len(ordinary_forms)
    assert all(not is_regional_species(species) for species in result)
    assert {species.name for species in result} == {
        "Rattata",
        "Meowth",
        "Growlithe",
        "Wooper",
    }


@pytest.mark.asyncio
async def test_repository_receives_selected_rarity():

    species = (create_species(id=1),)

    repository = FakeSpeciesRepository(species)

    rarity = Rarity.EPIC

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
        rarity_selector=FakeRaritySelector(Rarity.COMMON),
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
        rarity_selector=FakeRaritySelector(Rarity.COMMON),
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
