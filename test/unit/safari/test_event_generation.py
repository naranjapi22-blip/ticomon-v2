from dataclasses import replace

import pytest

from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import RARITY_CONFIG, Rarity
from core.safari import (
    SafariComposition,
    SafariEncounterContext,
    SafariEncounterGenerationError,
    SafariEncounterGenerator,
    SafariGeneratedEncounter,
    SafariMap,
    SafariPhase,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)
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


class ScriptedRandom:
    def __init__(
        self,
        *,
        event_order=(),
        species_ids=(),
        counts=(),
    ) -> None:
        self.event_order = list(event_order)
        self.species_ids = list(species_ids)
        self.counts = list(counts)
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
            selected_id = self.species_ids.pop(0)
            selected = next(
                species for species in candidates if species.id == selected_id
            )
            return [selected]
        return [candidates[0]]

    def choice(self, candidates):
        candidates = tuple(candidates)
        if self.counts:
            selected = self.counts.pop(0)
            assert selected in candidates
            return selected
        return candidates[0]


def make_species(
    species_id: int,
    *,
    types: list[str] | None = None,
    is_baby: bool = False,
    is_legendary: bool = False,
    is_mythical: bool = False,
    pokeapi_id: int | None = None,
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


def make_context(**overrides) -> SafariEncounterContext:
    values = {
        "safari_map": SafariMap.FOREST,
        "zone": SafariZone.RIVERBANK,
        "weather": SafariWeather.CLEAR,
        "time_of_day": SafariTimeOfDay.DAY,
        "phase": SafariPhase.START,
        "map_type_weight_modifiers": {},
        "zone_type_weight_modifiers": {},
        "route_type_weight_modifiers": {},
        "seen_species_ids": frozenset(),
        "route_allowed_events": frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.FISHING}
        ),
    }
    values.update(overrides)
    return SafariEncounterContext(**values)


def make_generator(species, random_source=None):
    repository = FakeSpeciesRepository(species)
    factory = RecordingOpportunityFactory()
    random_source = random_source or ScriptedRandom()
    generator = SafariEncounterGenerator(
        repository,  # type: ignore[arg-type]
        factory,  # type: ignore[arg-type]
        random_source,  # type: ignore[arg-type]
    )
    return generator, repository, factory, random_source


@pytest.mark.asyncio
async def test_fishing_requires_water_candidates():
    water = make_species(1, types=["water"])
    fire = make_species(2, types=["fire"])
    random_source = ScriptedRandom(event_order=(SafariThematicEvent.FISHING,))
    generator, _, _, _ = make_generator((water, fire), random_source)

    result = await generator.generate_with_events(
        make_context(),
        (SafariComposition.NORMAL,),
    )

    assert result.event == SafariThematicEvent.FISHING
    assert {slot.species_id for slot in result.encounter.slots} == {1}


@pytest.mark.asyncio
async def test_volcanic_event_multiplies_type_weight_and_dual_type_uses_maximum():
    fire_rock = make_species(1, types=["fire", "rock"])
    neutral = make_species(2, types=["normal"])
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.VOLCANIC_ACTIVITY,),
        species_ids=(1,),
    )
    generator, _, _, _ = make_generator((fire_rock, neutral), random_source)
    context = make_context(
        safari_map=SafariMap.MOUNTAIN,
        zone=SafariZone.ROCKY_SLOPE,
        phase=SafariPhase.DEVELOPMENT,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.VOLCANIC_ACTIVITY}
        ),
    )

    result = await generator.generate_with_events(
        context,
        (SafariComposition.NORMAL,),
    )
    _, weights = random_source.species_calls[0]
    base_weight = RARITY_CONFIG[Rarity.COMMON].spawn_weight

    assert result.event == SafariThematicEvent.VOLCANIC_ACTIVITY
    assert weights == (base_weight * 1.7 * 1.3, base_weight)


@pytest.mark.asyncio
async def test_graveyard_favors_ghost_without_requiring_it():
    ghost = make_species(1, types=["ghost"])
    normal = make_species(2, types=["normal"])
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.GRAVEYARD,),
        species_ids=(1,),
    )
    generator, _, _, _ = make_generator((ghost, normal), random_source)
    context = make_context(
        safari_map=SafariMap.SWAMP,
        zone=SafariZone.DEAD_FOREST,
        phase=SafariPhase.DEVELOPMENT,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.GRAVEYARD}
        ),
    )

    await generator.generate_with_events(context, (SafariComposition.NORMAL,))
    _, weights = random_source.species_calls[0]
    base_weight = RARITY_CONFIG[Rarity.COMMON].spawn_weight

    assert weights == (base_weight * 1.8, base_weight)


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
async def test_weather_and_time_remain_neutral_with_events(
    first_overrides,
    second_overrides,
):
    catalog = (make_species(1, types=["fire"]), make_species(2))
    base_context = {
        "safari_map": SafariMap.MOUNTAIN,
        "zone": SafariZone.ROCKY_SLOPE,
        "phase": SafariPhase.DEVELOPMENT,
        "route_allowed_events": frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.VOLCANIC_ACTIVITY}
        ),
    }
    first_random = ScriptedRandom(event_order=(SafariThematicEvent.VOLCANIC_ACTIVITY,))
    second_random = ScriptedRandom(event_order=(SafariThematicEvent.VOLCANIC_ACTIVITY,))
    first_generator, _, _, _ = make_generator(catalog, first_random)
    second_generator, _, _, _ = make_generator(catalog, second_random)

    await first_generator.generate_with_events(
        make_context(**base_context, **first_overrides),
        (SafariComposition.SOLITARY,),
    )
    await second_generator.generate_with_events(
        make_context(**base_context, **second_overrides),
        (SafariComposition.SOLITARY,),
    )

    assert first_random.species_calls[0][1] == second_random.species_calls[0][1]


@pytest.mark.asyncio
async def test_nest_works_with_baby_nest_and_independent_opportunities():
    babies = (
        make_species(1, types=["grass"], is_baby=True),
        make_species(2, types=["bug"], is_baby=True),
        make_species(3, types=["normal"], is_baby=True),
    )
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.NEST,),
        counts=(3,),
    )
    generator, _, factory, _ = make_generator(babies, random_source)
    context = make_context(
        safari_map=SafariMap.SWAMP,
        zone=SafariZone.DENSE_REEDS,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.NEST}
        ),
    )

    result = await generator.generate_with_events(
        context,
        (SafariComposition.BABY_NEST,),
    )

    assert result.event == SafariThematicEvent.NEST
    assert len(result.encounter.slots) == 3
    assert all(
        slot.opportunity.species.metadata.is_baby for slot in result.encounter.slots
    )
    assert len({id(opportunity) for opportunity in factory.opportunities}) == 3


@pytest.mark.asyncio
async def test_none_reproduces_phase_eight_without_implicit_event_selection():
    catalog = (make_species(1), make_species(2), make_species(3))
    normal_random = ScriptedRandom(species_ids=(2, 1, 3))
    event_random = ScriptedRandom(
        event_order=(SafariThematicEvent.NONE,),
        species_ids=(2, 1, 3),
    )
    normal_generator, _, _, _ = make_generator(catalog, normal_random)
    event_generator, _, _, _ = make_generator(catalog, event_random)
    context = make_context(route_allowed_events=frozenset({SafariThematicEvent.NONE}))

    encounter = await normal_generator.generate(context, SafariComposition.NORMAL)
    generated = await event_generator.generate_with_events(
        context,
        (SafariComposition.NORMAL,),
    )

    assert generated.event == SafariThematicEvent.NONE
    assert [slot.species_id for slot in generated.encounter.slots] == [
        slot.species_id for slot in encounter.slots
    ]


@pytest.mark.asyncio
async def test_event_without_candidates_tries_next_event_once():
    fire = make_species(1, types=["fire"])
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.FISHING, SafariThematicEvent.NONE)
    )
    generator, _, _, _ = make_generator((fire,), random_source)

    result = await generator.generate_with_events(
        make_context(),
        (SafariComposition.NORMAL,),
    )

    assert result.event == SafariThematicEvent.NONE
    assert [len(call[0]) for call in random_source.event_calls] == [2, 1]


@pytest.mark.asyncio
async def test_failed_events_and_composition_continue_in_requested_order():
    normal = make_species(1)
    regional = make_species(2, pokeapi_id=10100)
    random_source = ScriptedRandom(
        event_order=(
            SafariThematicEvent.NEST,
            SafariThematicEvent.NONE,
            SafariThematicEvent.NONE,
        )
    )
    generator, repository, _, _ = make_generator((normal, regional), random_source)
    context = make_context(
        safari_map=SafariMap.SWAMP,
        zone=SafariZone.DENSE_REEDS,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.NEST}
        ),
    )

    result = await generator.generate_with_events(
        context,
        (SafariComposition.BABY_NEST, SafariComposition.SOLITARY),
    )

    assert result.encounter.composition == SafariComposition.SOLITARY
    assert result.event == SafariThematicEvent.NONE
    assert repository.get_all_calls == 1


@pytest.mark.asyncio
async def test_event_generation_deduplicates_compositions():
    normal = make_species(1)
    regional = make_species(2, pokeapi_id=10100)
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.NONE, SafariThematicEvent.NONE)
    )
    generator, _, _, _ = make_generator((normal, regional), random_source)
    context = make_context(route_allowed_events=frozenset({SafariThematicEvent.NONE}))

    result = await generator.generate_with_events(
        context,
        (
            SafariComposition.BABY_NEST,
            SafariComposition.BABY_NEST,
            SafariComposition.SOLITARY,
        ),
    )

    assert result.encounter.composition == SafariComposition.SOLITARY
    assert len(random_source.event_calls) == 2


@pytest.mark.asyncio
async def test_final_fallback_is_normal_none():
    normal = make_species(1)
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.NEST, SafariThematicEvent.NONE)
    )
    generator, _, _, _ = make_generator((normal,), random_source)
    context = make_context(
        safari_map=SafariMap.SWAMP,
        zone=SafariZone.DENSE_REEDS,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.NEST}
        ),
    )

    result = await generator.generate_with_events(
        context,
        (SafariComposition.BABY_NEST,),
    )

    assert result.event == SafariThematicEvent.NONE
    assert result.encounter.composition == SafariComposition.NORMAL


@pytest.mark.asyncio
async def test_empty_or_fully_excluded_catalog_fails_without_relaxing_filters():
    excluded = (
        make_species(1, is_legendary=True),
        make_species(2, is_mythical=True),
        make_species(3, pokeapi_id=10100),
        make_species(4),
    )
    generator, _, factory, _ = make_generator(excluded)

    with pytest.raises(SafariEncounterGenerationError):
        await generator.generate_with_events(
            make_context(seen_species_ids={4}),
            (SafariComposition.NORMAL,),
        )

    assert factory.opportunities == []


@pytest.mark.asyncio
async def test_generated_result_keeps_event_outside_encounter_and_context_unchanged():
    context = make_context()
    original_route_events = context.route_allowed_events
    generator, _, _, _ = make_generator(
        (make_species(1, types=["water"]),),
        ScriptedRandom(event_order=(SafariThematicEvent.FISHING,)),
    )

    result = await generator.generate_with_events(
        context,
        (SafariComposition.NORMAL,),
    )

    assert isinstance(result, SafariGeneratedEncounter)
    assert result.encounter.composition == SafariComposition.NORMAL
    assert result.event == SafariThematicEvent.FISHING
    assert result.encounter.event == SafariThematicEvent.FISHING
    assert context.route_allowed_events == original_route_events
    assert len({slot.id for slot in result.encounter.slots}) == len(
        result.encounter.slots
    )
