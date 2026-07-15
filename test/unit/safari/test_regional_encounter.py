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
    SafariGeneratedRegionalEncounter,
    SafariMap,
    SafariPhase,
    SafariRegionalEncounterForm,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)
from core.species import REGIONAL_POKEAPI_IDS, is_regional_species
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
        self.opportunities = []

    def create(self, species):
        opportunity = OpportunityFactory.create(species)
        self.opportunities.append(opportunity)
        return opportunity


class DistinctOpportunityFactory(RecordingOpportunityFactory):
    def create(self, species):
        opportunity = super().create(species)
        call_number = len(self.opportunities)
        opportunity.is_shiny = call_number % 2 == 0
        opportunity.initial_form = Variant(call_number, f"Regional {call_number}")
        return opportunity


class ScriptedRandom:
    def __init__(self, *, event_order=(), species_ids=()) -> None:
        self.event_order = list(event_order)
        self.species_ids = list(species_ids)
        self.event_calls = []
        self.species_calls = []

    def choices(self, candidates, weights, k):
        assert k == 1
        candidates = tuple(candidates)
        weights = tuple(weights)
        if candidates and isinstance(candidates[0], SafariThematicEvent):
            self.event_calls.append((candidates, weights))
            if self.event_order:
                selected = self.event_order.pop(0)
                assert selected in candidates
                return [selected]
            return [candidates[0]]

        self.species_calls.append((candidates, weights))
        if self.species_ids:
            species_id = self.species_ids.pop(0)
            return [next(item for item in candidates if item.id == species_id)]
        return [candidates[0]]

    @staticmethod
    def choice(candidates):
        return tuple(candidates)[0]


def make_species(
    species_id: int,
    *,
    pokeapi_id: int | None = None,
    types: list[str] | None = None,
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
        spawn_rarity=Rarity.COMMON,
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


def make_context(**overrides) -> SafariEncounterContext:
    values = {
        "safari_map": SafariMap.FOREST,
        "zone": SafariZone.FOREST_ENTRANCE,
        "weather": SafariWeather.CLEAR,
        "time_of_day": SafariTimeOfDay.DAY,
        "phase": SafariPhase.DEVELOPMENT,
        "map_type_weight_modifiers": {},
        "zone_type_weight_modifiers": {},
        "route_type_weight_modifiers": {},
        "seen_species_ids": frozenset(),
        "route_allowed_events": frozenset({SafariThematicEvent.NONE}),
    }
    values.update(overrides)
    return SafariEncounterContext(**values)


def make_generator(species, random_source=None, factory=None):
    repository = FakeSpeciesRepository(species)
    factory = factory or RecordingOpportunityFactory()
    random_source = random_source or ScriptedRandom()
    generator = SafariEncounterGenerator(
        repository,  # type: ignore[arg-type]
        factory,  # type: ignore[arg-type]
        random_source,  # type: ignore[arg-type]
    )
    return generator, repository, factory, random_source


def test_regional_forms_are_exact_and_explicit():
    assert [form.value for form in SafariRegionalEncounterForm] == [
        "MIXED",
        "SOLITARY",
        "HERD",
    ]


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
async def test_regional_species_remain_excluded_from_common_compositions(composition):
    regional = make_regional(100, is_baby=True)
    ordinary = tuple(make_species(index, is_baby=True) for index in range(1, 4))
    generator, _, _, _ = make_generator((regional, *ordinary))

    encounter = await generator.generate(make_context(), composition)

    assert all(
        not is_regional_species(slot.opportunity.species) for slot in encounter.slots
    )


@pytest.mark.asyncio
async def test_ordinary_event_generation_cannot_introduce_regional_species():
    regional_water = make_regional(100, types=["water"])
    ordinary_water = make_species(1, types=["water"])
    random_source = ScriptedRandom(event_order=(SafariThematicEvent.FISHING,))
    generator, _, _, _ = make_generator(
        (regional_water, ordinary_water),
        random_source,
    )
    context = make_context(
        zone=SafariZone.RIVERBANK,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.FISHING}
        ),
    )

    result = await generator.generate_with_events(
        context,
        (SafariComposition.NORMAL,),
    )

    assert result.event == SafariThematicEvent.FISHING
    assert {slot.species_id for slot in result.encounter.slots} == {1}


@pytest.mark.asyncio
async def test_start_rejects_regional_generation_before_loading_catalog():
    generator, repository, _, _ = make_generator((make_regional(100),))

    with pytest.raises(SafariEncounterGenerationError, match="START"):
        await generator.generate_regional(
            make_context(phase=SafariPhase.START),
            SafariRegionalEncounterForm.SOLITARY,
        )

    assert repository.get_all_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [SafariPhase.DEVELOPMENT, SafariPhase.FINAL])
async def test_development_and_final_allow_regional_generation(phase):
    generator, _, _, _ = make_generator((make_regional(100),))

    result = await generator.generate_regional(
        make_context(phase=phase),
        SafariRegionalEncounterForm.SOLITARY,
    )

    assert result.encounter.composition == SafariComposition.REGIONAL
    assert all(
        slot.capture_policy is SafariCapturePolicy.SHARED
        for slot in result.encounter.slots
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("ordinary_count", "slot_count"), [(1, 2), (2, 3), (3, 3)])
async def test_mixed_encounter_contains_one_regional_and_up_to_two_ordinary(
    ordinary_count,
    slot_count,
):
    regional = make_regional(100)
    ordinary = tuple(make_species(index) for index in range(1, ordinary_count + 1))
    generator, _, factory, _ = make_generator((regional, *ordinary))

    result = await generator.generate_regional(
        make_context(),
        SafariRegionalEncounterForm.MIXED,
    )
    species = [slot.opportunity.species for slot in result.encounter.slots]

    assert len(species) == slot_count
    assert sum(is_regional_species(item) for item in species) == 1
    assert len({item.id for item in species}) == slot_count
    assert len({id(item) for item in factory.opportunities}) == slot_count
    assert len({slot.id for slot in result.encounter.slots}) == slot_count
    assert not result.encounter.is_regional_herd
    assert result.encounter.slots[0].capture_policy is SafariCapturePolicy.SHARED


@pytest.mark.asyncio
async def test_mixed_encounter_fails_without_ordinary_species():
    generator, _, _, _ = make_generator((make_regional(100),))

    with pytest.raises(SafariEncounterGenerationError, match="ordinary"):
        await generator.generate_regional(
            make_context(),
            SafariRegionalEncounterForm.MIXED,
        )


@pytest.mark.asyncio
async def test_solitary_has_one_regional_slot_and_is_not_a_herd():
    generator, _, _, _ = make_generator((make_regional(100),))

    result = await generator.generate_regional(
        make_context(),
        SafariRegionalEncounterForm.SOLITARY,
    )

    assert isinstance(result, SafariGeneratedRegionalEncounter)
    assert result.regional_form == SafariRegionalEncounterForm.SOLITARY
    assert len(result.encounter.slots) == 1
    assert is_regional_species(result.encounter.slots[0].opportunity.species)
    assert not result.encounter.is_regional_herd


@pytest.mark.asyncio
async def test_regional_herd_has_one_population_slot_and_sets_flag():
    factory = DistinctOpportunityFactory()
    generator, _, _, _ = make_generator(
        (make_regional(100),),
        factory=factory,
    )

    result = await generator.generate_regional(
        make_context(),
        SafariRegionalEncounterForm.HERD,
    )
    opportunities = [slot.opportunity for slot in result.encounter.slots]

    assert result.regional_form == SafariRegionalEncounterForm.HERD
    assert len(opportunities) == 1
    assert {opportunity.species.id for opportunity in opportunities} == {100}
    assert len({id(opportunity) for opportunity in opportunities}) == 1
    assert len({slot.id for slot in result.encounter.slots}) == 1
    assert result.encounter.is_regional_herd
    shiny_values = [opportunity.is_shiny for opportunity in opportunities]
    assert shiny_values == [False]
    assert [opportunity.initial_form.name for opportunity in opportunities] == [
        "Regional 1",
    ]


@pytest.mark.asyncio
async def test_seen_species_uses_internal_id_without_linking_normal_and_regional():
    normal = make_species(1, pokeapi_id=25)
    regional = make_regional(9000, pokeapi_id=10091)
    generator, _, _, _ = make_generator((normal, regional))

    regional_result = await generator.generate_regional(
        make_context(seen_species_ids={normal.id}),
        SafariRegionalEncounterForm.SOLITARY,
    )
    ordinary_result = await generator.generate(
        make_context(seen_species_ids={regional.id}),
        SafariComposition.NORMAL,
    )

    assert regional_result.encounter.slots[0].species_id == regional.id
    assert ordinary_result.slots[0].species_id == normal.id


@pytest.mark.asyncio
async def test_seen_regional_is_excluded_without_excluding_another_regional():
    first = make_regional(100, pokeapi_id=10091)
    second = make_regional(200, pokeapi_id=10100)
    generator, _, _, _ = make_generator((first, second))

    result = await generator.generate_regional(
        make_context(seen_species_ids={first.id}),
        SafariRegionalEncounterForm.SOLITARY,
    )

    assert result.encounter.slots[0].species_id == second.id


@pytest.mark.asyncio
async def test_regional_legendary_and_mythical_flags_remain_excluded():
    catalog = (
        make_regional(100, is_legendary=True),
        make_regional(200, pokeapi_id=10100, is_mythical=True),
    )
    generator, _, factory, _ = make_generator(catalog)

    with pytest.raises(SafariEncounterGenerationError):
        await generator.generate_regional(
            make_context(),
            SafariRegionalEncounterForm.SOLITARY,
        )

    assert factory.opportunities == []


@pytest.mark.asyncio
async def test_compatible_event_modifies_regional_weights_using_dual_type_maximum():
    fire_rock = make_regional(100, types=["fire", "rock"])
    neutral = make_regional(200, pokeapi_id=10100, types=["normal"])
    random_source = ScriptedRandom(species_ids=(100,))
    generator, _, _, _ = make_generator((fire_rock, neutral), random_source)
    context = make_context(
        safari_map=SafariMap.MOUNTAIN,
        zone=SafariZone.ROCKY_SLOPE,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.VOLCANIC_ACTIVITY}
        ),
    )

    result = await generator.generate_regional(
        context,
        SafariRegionalEncounterForm.SOLITARY,
        SafariThematicEvent.VOLCANIC_ACTIVITY,
    )
    _, weights = random_source.species_calls[0]
    base_weight = RARITY_CONFIG[Rarity.COMMON].spawn_weight

    assert result.event == SafariThematicEvent.VOLCANIC_ACTIVITY
    assert weights == (base_weight * 1.7 * 1.3, base_weight)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first_overrides", "second_overrides"),
    [
        (
            {"weather": SafariWeather.CLEAR},
            {"weather": SafariWeather.SNOW},
        ),
        (
            {"time_of_day": SafariTimeOfDay.DAY},
            {"time_of_day": SafariTimeOfDay.NIGHT},
        ),
    ],
)
async def test_weather_and_time_remain_neutral_for_regional_weights(
    first_overrides,
    second_overrides,
):
    catalog = (
        make_regional(100, types=["fire"]),
        make_regional(200, pokeapi_id=10100, types=["normal"]),
    )
    base_context = {
        "safari_map": SafariMap.MOUNTAIN,
        "zone": SafariZone.ROCKY_SLOPE,
        "route_allowed_events": frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.VOLCANIC_ACTIVITY}
        ),
    }
    first_random = ScriptedRandom(species_ids=(100,))
    second_random = ScriptedRandom(species_ids=(100,))
    first_generator, _, _, _ = make_generator(catalog, first_random)
    second_generator, _, _, _ = make_generator(catalog, second_random)

    await first_generator.generate_regional(
        make_context(**base_context, **first_overrides),
        SafariRegionalEncounterForm.SOLITARY,
        SafariThematicEvent.VOLCANIC_ACTIVITY,
    )
    await second_generator.generate_regional(
        make_context(**base_context, **second_overrides),
        SafariRegionalEncounterForm.SOLITARY,
        SafariThematicEvent.VOLCANIC_ACTIVITY,
    )

    assert first_random.species_calls[0][1] == second_random.species_calls[0][1]


@pytest.mark.asyncio
async def test_event_without_regional_candidates_allows_next_event():
    regional_fire = make_regional(100, types=["fire"])
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.FISHING, SafariThematicEvent.NONE)
    )
    generator, _, _, _ = make_generator((regional_fire,), random_source)
    context = make_context(
        zone=SafariZone.RIVERBANK,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.FISHING}
        ),
    )

    result = await generator.generate_regional_with_events(
        context,
        (SafariRegionalEncounterForm.SOLITARY,),
    )

    assert result.event == SafariThematicEvent.NONE
    assert [len(call[0]) for call in random_source.event_calls] == [2, 1]


@pytest.mark.asyncio
async def test_impossible_form_allows_next_regional_form_without_ordinary_fallback():
    regional = make_regional(100)
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.NONE, SafariThematicEvent.NONE)
    )
    generator, _, _, _ = make_generator((regional,), random_source)

    result = await generator.generate_regional_with_events(
        make_context(),
        (
            SafariRegionalEncounterForm.MIXED,
            SafariRegionalEncounterForm.MIXED,
            SafariRegionalEncounterForm.SOLITARY,
        ),
    )

    assert result.regional_form == SafariRegionalEncounterForm.SOLITARY
    assert result.encounter.composition == SafariComposition.REGIONAL
    assert len(random_source.event_calls) == 2


@pytest.mark.asyncio
async def test_all_regional_forms_fail_without_degrading_to_common_encounter():
    generator, _, factory, _ = make_generator((make_species(1),))

    with pytest.raises(SafariEncounterGenerationError, match="no regional"):
        await generator.generate_regional_with_events(
            make_context(),
            (
                SafariRegionalEncounterForm.MIXED,
                SafariRegionalEncounterForm.SOLITARY,
                SafariRegionalEncounterForm.HERD,
            ),
        )

    assert factory.opportunities == []


@pytest.mark.asyncio
@pytest.mark.parametrize("pokeapi_id", sorted(REGIONAL_POKEAPI_IDS))
async def test_every_regional_catalog_entry_has_a_real_generation_path(pokeapi_id):
    internal_id = 50000 + pokeapi_id
    regional = make_regional(
        internal_id,
        pokeapi_id=pokeapi_id,
        types=["normal"],
    )
    generator, _, _, _ = make_generator((regional,))

    result = await generator.generate_regional(
        make_context(),
        SafariRegionalEncounterForm.SOLITARY,
    )

    assert result.encounter.slots[0].species_id == internal_id
    assert is_regional_species(result.encounter.slots[0].opportunity.species)
