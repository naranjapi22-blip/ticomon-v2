from dataclasses import replace

import pytest

from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import RARITY_CONFIG, Rarity
from core.safari import (
    SafariComposition,
    SafariEncounterContext,
    SafariEncounterGenerationError,
    SafariEncounterGenerator,
    SafariMap,
    SafariPhase,
    SafariSlotStatus,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)
from core.species.regional_species import is_regional_species
from test.factories import create_species


class FakeSpeciesRepository:
    def __init__(self, species) -> None:
        self.species = tuple(species)
        self.get_all_calls = 0

    async def get_all(self):
        self.get_all_calls += 1
        return self.species


class RecordingOpportunityFactory:
    def __init__(self) -> None:
        self.species = []
        self.opportunities = []

    def create(self, species):
        opportunity = OpportunityFactory.create(species)
        self.species.append(species)
        self.opportunities.append(opportunity)
        return opportunity


class FakeWeightedRandom:
    def __init__(self, selected_ids=()) -> None:
        self.selected_ids = list(selected_ids)
        self.calls = []

    def choices(self, candidates, weights, k):
        assert k == 1
        candidates = tuple(candidates)
        weights = tuple(weights)
        self.calls.append((candidates, weights))
        if self.selected_ids:
            selected_id = self.selected_ids.pop(0)
            return [next(item for item in candidates if item.id == selected_id)]
        return [candidates[0]]


def make_context(**overrides) -> SafariEncounterContext:
    values = {
        "safari_map": SafariMap.FOREST,
        "zone": SafariZone.FOREST_ENTRANCE,
        "weather": SafariWeather.CLEAR,
        "time_of_day": SafariTimeOfDay.DAY,
        "phase": SafariPhase.START,
        "map_type_weight_modifiers": {},
        "zone_type_weight_modifiers": {},
        "route_type_weight_modifiers": {},
        "seen_species_ids": frozenset(),
    }
    values.update(overrides)
    return SafariEncounterContext(**values)


def make_species(
    species_id: int,
    *,
    pokeapi_id: int | None = None,
    types: list[str] | None = None,
    rarity: Rarity = Rarity.COMMON,
    is_baby: bool = False,
    is_legendary: bool = False,
    is_mythical: bool = False,
):
    species = create_species(
        id=species_id,
        types=types,
        is_baby=is_baby,
        is_legendary=is_legendary,
        is_mythical=is_mythical,
    )
    return replace(
        species,
        pokeapi_id=pokeapi_id or species_id,
        spawn_rarity=rarity,
    )


def make_generator(species, random_source=None):
    repository = FakeSpeciesRepository(species)
    factory = RecordingOpportunityFactory()
    random_source = random_source or FakeWeightedRandom()
    generator = SafariEncounterGenerator(
        repository,  # type: ignore[arg-type]
        factory,  # type: ignore[arg-type]
        random_source,  # type: ignore[arg-type]
    )
    return generator, repository, factory, random_source


@pytest.mark.asyncio
async def test_generator_filters_seen_regional_legendary_and_mythical_species():
    seen = make_species(1)
    regional = make_species(9999, pokeapi_id=10100)
    legendary = make_species(3, is_legendary=True)
    mythical = make_species(4, is_mythical=True)
    baby = make_species(5, is_baby=True)
    normal = make_species(6)
    catalog = (seen, regional, legendary, mythical, baby, normal)
    generator, repository, _, _ = make_generator(catalog)

    encounter = await generator.generate(make_context(seen_species_ids={1}))

    assert {slot.species_id for slot in encounter.slots} == {5, 6}
    assert repository.species == catalog
    assert is_regional_species(regional)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("candidate_count", "expected_slot_count"),
    [(4, 3), (3, 3), (2, 2), (1, 1)],
)
async def test_generator_uses_up_to_three_distinct_species(
    candidate_count,
    expected_slot_count,
):
    catalog = tuple(make_species(index + 1) for index in range(candidate_count))
    generator, _, _, _ = make_generator(catalog)

    encounter = await generator.generate(make_context())
    species_ids = [slot.species_id for slot in encounter.slots]

    assert len(encounter.slots) == expected_slot_count
    assert len(species_ids) == len(set(species_ids))


@pytest.mark.asyncio
async def test_generator_does_not_relax_filters_when_no_candidate_remains():
    catalog = (
        make_species(1, is_legendary=True),
        make_species(2, pokeapi_id=10100),
    )
    generator, _, factory, _ = make_generator(catalog)

    with pytest.raises(SafariEncounterGenerationError):
        await generator.generate(make_context())

    assert factory.species == []


@pytest.mark.asyncio
async def test_spawn_rarity_supplies_the_canonical_base_weight():
    common = make_species(1, rarity=Rarity.COMMON)
    rare = make_species(2, rarity=Rarity.RARE)
    generator, _, _, random_source = make_generator((common, rare))

    await generator.generate(make_context())
    _, weights = random_source.calls[0]

    assert weights == (
        RARITY_CONFIG[Rarity.COMMON].spawn_weight,
        RARITY_CONFIG[Rarity.RARE].spawn_weight,
    )


@pytest.mark.asyncio
async def test_map_zone_and_route_modifiers_are_multiplied():
    fire = make_species(1, types=["fire"])
    neutral = make_species(2, types=["normal"])
    generator, _, _, random_source = make_generator((fire, neutral))
    context = make_context(
        map_type_weight_modifiers={"fire": 2.0},
        zone_type_weight_modifiers={"fire": 3.0},
        route_type_weight_modifiers={"fire": 4.0},
    )

    await generator.generate(context)
    _, weights = random_source.calls[0]
    base_weight = RARITY_CONFIG[Rarity.COMMON].spawn_weight

    assert weights == (base_weight * 2 * 3 * 4, base_weight)


@pytest.mark.asyncio
async def test_dual_type_uses_highest_modifier_once_per_source():
    dual = make_species(1, types=["fire", "water"])
    generator, _, _, random_source = make_generator((dual,))
    context = make_context(
        map_type_weight_modifiers={"fire": 2.0, "water": 3.0},
        zone_type_weight_modifiers={"fire": 4.0, "water": 1.0},
        route_type_weight_modifiers={"fire": 1.0, "water": 5.0},
    )

    await generator.generate(context)
    _, weights = random_source.calls[0]

    assert weights == (RARITY_CONFIG[Rarity.COMMON].spawn_weight * 3 * 4 * 5,)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_context", "second_context"),
    [
        (
            {"weather": SafariWeather.CLEAR},
            {"weather": SafariWeather.FOG},
        ),
        (
            {"time_of_day": SafariTimeOfDay.DAY},
            {"time_of_day": SafariTimeOfDay.NIGHT},
        ),
    ],
)
async def test_weather_and_time_do_not_change_species_weights_yet(
    first_context,
    second_context,
):
    catalog = (make_species(1, types=["grass"]), make_species(2, types=["bug"]))
    first_generator, _, _, first_random = make_generator(catalog)
    second_generator, _, _, second_random = make_generator(catalog)
    modifiers = {
        "map_type_weight_modifiers": {"grass": 1.5},
        "zone_type_weight_modifiers": {"bug": 1.2},
    }

    await first_generator.generate(
        make_context(
            **modifiers,
            **first_context,
        )
    )
    await second_generator.generate(
        make_context(
            **modifiers,
            **second_context,
        )
    )

    assert first_random.calls[0][1] == second_random.calls[0][1]


@pytest.mark.asyncio
async def test_zero_weight_excludes_candidates_and_all_zero_fails():
    fire = make_species(1, types=["fire"])
    water = make_species(2, types=["water"])
    generator, _, _, _ = make_generator((fire, water))

    encounter = await generator.generate(
        make_context(route_type_weight_modifiers={"fire": 0.0})
    )
    assert [slot.species_id for slot in encounter.slots] == [2]

    with pytest.raises(SafariEncounterGenerationError):
        await generator.generate(
            make_context(route_type_weight_modifiers={"fire": 0.0, "water": 0.0})
        )


@pytest.mark.asyncio
async def test_fake_random_controls_weighted_selection_without_replacement():
    catalog = tuple(make_species(index) for index in range(1, 5))
    random_source = FakeWeightedRandom(selected_ids=(3, 1, 4))
    generator, _, _, _ = make_generator(catalog, random_source)

    encounter = await generator.generate(make_context())

    assert [slot.species_id for slot in encounter.slots] == [3, 1, 4]
    assert [len(call[0]) for call in random_source.calls] == [4, 3, 2]
    assert 3 not in {species.id for species in random_source.calls[1][0]}
    assert 1 not in {species.id for species in random_source.calls[2][0]}


@pytest.mark.asyncio
async def test_factory_creates_independent_opportunity_and_slot_per_species():
    catalog = tuple(make_species(index) for index in range(1, 4))
    generator, repository, factory, _ = make_generator(catalog)

    encounter = await generator.generate(make_context())

    assert repository.get_all_calls == 1
    assert factory.species == list(catalog)
    assert len(factory.opportunities) == 3
    assert len({id(item) for item in factory.opportunities}) == 3
    assert [slot.opportunity for slot in encounter.slots] == factory.opportunities
    assert len({slot.id for slot in encounter.slots}) == 3
    assert all(slot.id.int > 0 for slot in encounter.slots)
    assert all(slot.status == SafariSlotStatus.AVAILABLE for slot in encounter.slots)
    assert encounter.composition == SafariComposition.NORMAL
    assert not encounter.is_regional_herd
    assert encounter.eligible_participant_ids == frozenset()


@pytest.mark.asyncio
async def test_thirteen_normal_encounters_do_not_repeat_species():
    catalog = tuple(make_species(index) for index in range(1, 46))
    generator, _, _, _ = make_generator(catalog)
    seen_species_ids: set[int] = set()

    for _ in range(13):
        encounter = await generator.generate(
            make_context(seen_species_ids=seen_species_ids)
        )
        encounter_species = [slot.opportunity.species for slot in encounter.slots]
        encounter_ids = {species.id for species in encounter_species}
        assert encounter.slots
        assert not (encounter_ids & seen_species_ids)
        assert all(not is_regional_species(species) for species in encounter_species)
        assert all(
            not species.metadata.is_legendary and not species.metadata.is_mythical
            for species in encounter_species
        )
        seen_species_ids.update(encounter_ids)

    assert len(seen_species_ids) == 39
