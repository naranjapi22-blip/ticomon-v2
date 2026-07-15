from dataclasses import replace

import pytest

from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import RARITY_CONFIG, Rarity
from core.safari import (
    SafariCapturePolicy,
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
from core.species.variant import Variant
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


class DistinctHerdOpportunityFactory:
    def __init__(self) -> None:
        self.call_count = 0

    def create(self, species):
        opportunity = OpportunityFactory.create(species)
        self.call_count += 1
        opportunity.is_shiny = self.call_count % 2 == 0
        opportunity.initial_form = Variant(
            id=self.call_count,
            name=f"Form {self.call_count}",
        )
        return opportunity


class FakeWeightedRandom:
    def __init__(self, selected_ids=(), choice_values=()) -> None:
        self.selected_ids = list(selected_ids)
        self.choice_values = list(choice_values)
        self.calls = []
        self.choice_calls = []

    def choices(self, candidates, weights, k):
        assert k == 1
        candidates = tuple(candidates)
        weights = tuple(weights)
        self.calls.append((candidates, weights))
        if self.selected_ids:
            selected_id = self.selected_ids.pop(0)
            return [next(item for item in candidates if item.id == selected_id)]
        return [candidates[0]]

    def choice(self, candidates):
        candidates = tuple(candidates)
        self.choice_calls.append(candidates)
        if self.choice_values:
            selected = self.choice_values.pop(0)
            assert selected in candidates
            return selected
        return candidates[0]


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


def make_regional(
    species_id: int,
    *,
    pokeapi_id: int = 10091,
    types: list[str] | None = None,
    **metadata,
):
    return make_species(
        species_id,
        pokeapi_id=pokeapi_id,
        types=types,
        **metadata,
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
async def test_dual_type_combines_matching_modifiers_per_source():
    dual = make_species(1, types=["fire", "water"])
    generator, _, _, random_source = make_generator((dual,))
    context = make_context(
        map_type_weight_modifiers={"fire": 2.0, "water": 3.0},
        zone_type_weight_modifiers={"fire": 4.0, "water": 1.0},
        route_type_weight_modifiers={"fire": 1.0, "water": 5.0},
    )

    await generator.generate(context)
    _, weights = random_source.calls[0]

    assert weights == (RARITY_CONFIG[Rarity.COMMON].spawn_weight * 6 * 4 * 5,)


@pytest.mark.asyncio
async def test_affine_species_outweighs_neutral_species_in_matching_context():
    coast_species = make_species(1, types=["water", "rock"])
    neutral_species = make_species(2, types=["normal"])
    generator, _, _, random_source = make_generator((coast_species, neutral_species))
    context = make_context(
        map_type_weight_modifiers={"water": 1.4, "rock": 1.1},
        zone_type_weight_modifiers={"water": 1.5, "rock": 1.2},
        route_type_weight_modifiers={"water": 1.3, "rock": 1.1},
    )

    await generator.generate(context)
    _, weights = random_source.calls[0]

    assert weights[0] > weights[1]


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
    assert all(
        slot.capture_policy is SafariCapturePolicy.SHARED for slot in encounter.slots
    )
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


@pytest.mark.asyncio
async def test_explicit_normal_keeps_phase_seven_behavior():
    catalog = tuple(make_species(index) for index in range(1, 5))
    generator, _, _, _ = make_generator(catalog)

    encounter = await generator.generate(
        make_context(),
        SafariComposition.NORMAL,
    )

    assert encounter.composition == SafariComposition.NORMAL
    assert len(encounter.slots) == 3
    assert len({slot.species_id for slot in encounter.slots}) == 3


@pytest.mark.asyncio
async def test_duel_has_two_distinct_species_and_independent_opportunities():
    catalog = tuple(make_species(index) for index in range(1, 4))
    random_source = FakeWeightedRandom(selected_ids=(2, 3))
    generator, _, factory, _ = make_generator(catalog, random_source)

    encounter = await generator.generate(make_context(), SafariComposition.DUEL)

    assert encounter.composition == SafariComposition.DUEL
    assert [slot.species_id for slot in encounter.slots] == [2, 3]
    assert len({id(slot.opportunity) for slot in encounter.slots}) == 2
    assert factory.species == [catalog[1], catalog[2]]


@pytest.mark.asyncio
async def test_duel_fails_instead_of_degrading_with_one_candidate():
    generator, _, factory, _ = make_generator((make_species(1),))

    with pytest.raises(SafariEncounterGenerationError, match="DUEL"):
        await generator.generate(make_context(), SafariComposition.DUEL)

    assert factory.species == []


@pytest.mark.asyncio
@pytest.mark.parametrize("slot_count", [3, 4, 5])
async def test_herd_uses_one_population_slot(slot_count):
    catalog = (make_species(1), make_species(2))
    random_source = FakeWeightedRandom(selected_ids=(2,), choice_values=(slot_count,))
    generator, _, factory, _ = make_generator(catalog, random_source)

    encounter = await generator.generate(make_context(), SafariComposition.HERD)

    assert encounter.composition == SafariComposition.HERD
    assert len(encounter.slots) == 1
    assert {slot.species_id for slot in encounter.slots} == {2}
    assert len({slot.id for slot in encounter.slots}) == 1
    assert len({id(slot.opportunity) for slot in encounter.slots}) == 1
    assert factory.species == [catalog[1]]
    assert not encounter.is_regional_herd


@pytest.mark.asyncio
async def test_herd_preserves_generated_shiny_and_variant_values():
    repository = FakeSpeciesRepository((make_species(1),))
    factory = DistinctHerdOpportunityFactory()
    generator = SafariEncounterGenerator(
        repository,  # type: ignore[arg-type]
        factory,  # type: ignore[arg-type]
        FakeWeightedRandom(choice_values=(3,)),  # type: ignore[arg-type]
    )

    encounter = await generator.generate(make_context(), SafariComposition.HERD)

    assert [slot.opportunity.is_shiny for slot in encounter.slots] == [False]
    assert [slot.opportunity.initial_form.name for slot in encounter.slots] == [
        "Form 1"
    ]


@pytest.mark.asyncio
async def test_solitary_rejects_ordinary_and_regional_species():
    ordinary = make_species(1)
    regional = make_regional(2)
    generator, _, _, _ = make_generator(
        (ordinary, regional),
    )

    with pytest.raises(SafariEncounterGenerationError, match="unsupported"):
        await generator.generate(make_context(), SafariComposition.SOLITARY)


@pytest.mark.asyncio
async def test_common_generation_uses_requested_fallback_order():
    ordinary_a = make_species(1)
    ordinary_b = make_species(2)
    generator, _, _, _ = make_generator(
        (ordinary_a, ordinary_b),
        FakeWeightedRandom(),
    )

    encounter = await generator.generate_with_events(
        make_context(),
        (
            SafariComposition.DUEL,
            SafariComposition.NORMAL,
        ),
    )

    assert encounter.encounter.composition == SafariComposition.DUEL


@pytest.mark.asyncio
async def test_baby_nest_uses_exactly_two_when_only_two_babies_are_available():
    babies = (make_species(1, is_baby=True), make_species(2, is_baby=True))
    non_baby = make_species(3)
    generator, _, _, random_source = make_generator((*babies, non_baby))

    encounter = await generator.generate(make_context(), SafariComposition.BABY_NEST)

    assert encounter.composition == SafariComposition.BABY_NEST
    assert {slot.species_id for slot in encounter.slots} == {1, 2}
    assert random_source.choice_calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("slot_count", [2, 3])
async def test_baby_nest_count_is_controlled_when_three_babies_exist(slot_count):
    babies = tuple(make_species(index, is_baby=True) for index in range(1, 4))
    random_source = FakeWeightedRandom(choice_values=(slot_count,))
    generator, _, _, _ = make_generator(babies, random_source)

    encounter = await generator.generate(make_context(), SafariComposition.BABY_NEST)

    assert len(encounter.slots) == slot_count
    assert len({slot.species_id for slot in encounter.slots}) == slot_count
    assert all(slot.opportunity.species.metadata.is_baby for slot in encounter.slots)


@pytest.mark.asyncio
async def test_baby_nest_fails_with_one_baby_and_does_not_fill_with_non_baby():
    catalog = (make_species(1, is_baby=True), make_species(2))
    generator, _, factory, _ = make_generator(catalog)

    with pytest.raises(SafariEncounterGenerationError, match="BABY_NEST"):
        await generator.generate(make_context(), SafariComposition.BABY_NEST)

    assert factory.species == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "composition",
    [
        SafariComposition.NORMAL,
        SafariComposition.DUEL,
        SafariComposition.HERD,
        SafariComposition.BABY_NEST,
    ],
)
async def test_all_common_compositions_keep_base_exclusions(composition):
    valid_species = [
        make_species(1, is_baby=True),
        make_species(2, is_baby=True),
        make_regional(7, is_baby=True),
    ]
    catalog = (
        *valid_species,
        make_species(3, pokeapi_id=10100, is_baby=True),
        make_species(4, is_legendary=True, is_baby=True),
        make_species(5, is_mythical=True, is_baby=True),
        make_species(6, is_baby=True),
    )
    random_source = FakeWeightedRandom(choice_values=(3,))
    generator, _, _, _ = make_generator(catalog, random_source)

    encounter = await generator.generate(
        make_context(seen_species_ids={6}),
        composition,
    )

    assert {slot.species_id for slot in encounter.slots} <= {1, 2}


@pytest.mark.asyncio
async def test_fallback_tries_ordered_unique_compositions_then_succeeds():
    catalog = (make_species(1), make_species(2))
    generator, repository, _, _ = make_generator(catalog)

    encounter = await generator.generate_from_compositions(
        make_context(),
        (
            SafariComposition.BABY_NEST,
            SafariComposition.BABY_NEST,
            SafariComposition.DUEL,
        ),
    )

    assert encounter.composition == SafariComposition.DUEL
    assert repository.get_all_calls == 1


@pytest.mark.asyncio
async def test_fallback_uses_normal_only_after_requested_compositions_fail():
    generator, _, _, _ = make_generator((make_species(1),))

    encounter = await generator.generate_from_compositions(
        make_context(),
        (SafariComposition.BABY_NEST, SafariComposition.DUEL),
    )

    assert encounter.composition == SafariComposition.NORMAL
    assert len(encounter.slots) == 1


@pytest.mark.asyncio
async def test_fallback_fails_when_normal_cannot_generate_without_relaxing_filters():
    catalog = (
        make_species(1, is_legendary=True),
        make_regional(2),
    )
    generator, _, factory, _ = make_generator(catalog)

    with pytest.raises(
        SafariEncounterGenerationError,
        match="no common Safari composition",
    ):
        await generator.generate_from_compositions(
            make_context(seen_species_ids={2}),
            (SafariComposition.BABY_NEST, SafariComposition.NORMAL),
        )

    assert factory.species == []


@pytest.mark.asyncio
async def test_unsupported_extraordinary_composition_is_rejected():
    generator, repository, _, _ = make_generator((make_species(1),))

    with pytest.raises(SafariEncounterGenerationError, match="unsupported"):
        await generator.generate(make_context(), SafariComposition.LEGENDARY)

    assert repository.get_all_calls == 0


@pytest.mark.asyncio
async def test_common_composition_sequence_respects_seen_species():
    catalog = (
        tuple(make_species(index) for index in range(1, 11))
        + (make_regional(21),)
        + tuple(make_species(index, is_baby=True) for index in range(11, 21))
    )
    generator, _, _, _ = make_generator(catalog)
    seen_species_ids: set[int] = set()

    for composition in (
        SafariComposition.NORMAL,
        SafariComposition.DUEL,
        SafariComposition.HERD,
        SafariComposition.BABY_NEST,
    ):
        encounter = await generator.generate(
            make_context(seen_species_ids=seen_species_ids),
            composition,
        )
        encounter_species_ids = {slot.species_id for slot in encounter.slots}
        assert not (encounter_species_ids & seen_species_ids)
        seen_species_ids.update(encounter_species_ids)

    assert len(seen_species_ids) >= 8
