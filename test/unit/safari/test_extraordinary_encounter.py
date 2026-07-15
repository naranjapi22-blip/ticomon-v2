from dataclasses import replace
from uuid import uuid4

import pytest

from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import RARITY_CONFIG, Rarity
from core.safari import (
    SafariCapturePolicy,
    SafariComposition,
    SafariEncounter,
    SafariEncounterContext,
    SafariEncounterGenerationError,
    SafariEncounterGenerator,
    SafariEncounterSlot,
    SafariExtraordinaryFlags,
    SafariGeneratedEncounter,
    SafariGeneratedRegionalEncounter,
    SafariMap,
    SafariPhase,
    SafariRegionalEncounterForm,
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
        self.calls = []

    def create(self, species):
        self.calls.append(species)
        return OpportunityFactory.create(species)


class ScriptedRandom:
    def __init__(self, *, species_ids=(), event_order=()) -> None:
        self.species_ids = list(species_ids)
        self.event_order = list(event_order)
        self.species_calls = []
        self.event_calls = []

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
            return [next(species for species in candidates if species.id == species_id)]
        return [candidates[0]]

    @staticmethod
    def choice(candidates):
        return tuple(candidates)[0]


def make_species(
    species_id: int,
    *,
    types: list[str] | None = None,
    legendary: bool = False,
    mythical: bool = False,
    pokeapi_id: int | None = None,
):
    species = create_species(
        id=species_id,
        types=types,
        is_legendary=legendary,
        is_mythical=mythical,
    )
    return replace(
        species,
        pokeapi_id=pokeapi_id or species_id,
        spawn_rarity=Rarity.COMMON,
    )


def make_context(**overrides) -> SafariEncounterContext:
    values = {
        "safari_map": SafariMap.FOREST,
        "zone": SafariZone.FOREST_ENTRANCE,
        "weather": SafariWeather.CLEAR,
        "time_of_day": SafariTimeOfDay.DAY,
        "phase": SafariPhase.FINAL,
        "map_type_weight_modifiers": {},
        "zone_type_weight_modifiers": {},
        "route_type_weight_modifiers": {},
        "seen_species_ids": frozenset(),
        "route_allowed_events": frozenset({SafariThematicEvent.NONE}),
        "extraordinary_flags": SafariExtraordinaryFlags(),
    }
    values.update(overrides)
    return SafariEncounterContext(**values)


def make_generator(species=(), *, random_source=None, factory=None):
    repository = FakeSpeciesRepository(species)
    random_source = random_source or ScriptedRandom()
    factory = factory or RecordingOpportunityFactory()
    generator = SafariEncounterGenerator(
        repository,  # type: ignore[arg-type]
        factory,  # type: ignore[arg-type]
        random_source,  # type: ignore[arg-type]
    )
    return generator, repository, factory, random_source


def make_encounter(
    composition: SafariComposition = SafariComposition.NORMAL,
    *,
    slot_count: int = 2,
    regional_herd: bool = False,
) -> SafariEncounter:
    slots = tuple(
        SafariEncounterSlot(
            uuid4(),
            OpportunityFactory.create(make_species(index + 1)),
        )
        for index in range(slot_count)
    )
    return SafariEncounter(
        uuid4(),
        composition,
        slots,
        is_regional_herd=regional_herd,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [SafariPhase.START, SafariPhase.DEVELOPMENT])
@pytest.mark.parametrize("method_name", ["generate_legendary", "generate_mythical"])
async def test_extraordinary_species_are_rejected_before_final(phase, method_name):
    generator, repository, _, _ = make_generator()

    with pytest.raises(SafariEncounterGenerationError, match="FINAL"):
        await getattr(generator, method_name)(make_context(phase=phase))

    assert repository.get_all_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "composition", "metadata_field"),
    [
        ("generate_legendary", SafariComposition.LEGENDARY, "is_legendary"),
        ("generate_mythical", SafariComposition.MYTHICAL, "is_mythical"),
    ],
)
async def test_extraordinary_generation_has_one_matching_slot(
    method_name,
    composition,
    metadata_field,
):
    selected = make_species(
        1,
        legendary=composition == SafariComposition.LEGENDARY,
        mythical=composition == SafariComposition.MYTHICAL,
    )
    generator, _, factory, _ = make_generator((selected,))

    result = await getattr(generator, method_name)(make_context())

    assert result.encounter.composition == composition
    assert len(result.encounter.slots) == 1
    metadata = result.encounter.slots[0].opportunity.species.metadata
    assert getattr(metadata, metadata_field)
    assert result.encounter.slots[0].capture_policy is SafariCapturePolicy.UNIQUE
    assert len(factory.calls) == 1
    assert result.event == SafariThematicEvent.NONE


@pytest.mark.asyncio
async def test_legendary_and_mythical_filters_are_exclusive_and_respect_seen():
    legendary = make_species(1, legendary=True)
    mythical = make_species(2, mythical=True)
    both = make_species(3, legendary=True, mythical=True)
    generator, _, _, _ = make_generator((legendary, mythical, both))

    with pytest.raises(SafariEncounterGenerationError, match="LEGENDARY"):
        await generator.generate_legendary(make_context(seen_species_ids={1}))
    with pytest.raises(SafariEncounterGenerationError, match="MYTHICAL"):
        await generator.generate_mythical(make_context(seen_species_ids={2}))


@pytest.mark.asyncio
async def test_regional_extraordinary_species_are_not_assumed_supported():
    regional_legendary = make_species(1, legendary=True, pokeapi_id=10091)
    generator, _, _, _ = make_generator((regional_legendary,))

    with pytest.raises(SafariEncounterGenerationError, match="LEGENDARY"):
        await generator.generate_legendary(make_context())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "flags"),
    [
        (
            "generate_legendary",
            SafariExtraordinaryFlags(legendary_seen=True),
        ),
        (
            "generate_mythical",
            SafariExtraordinaryFlags(mythical_seen=True),
        ),
    ],
)
async def test_prior_flag_blocks_specific_extraordinary_generation(method_name, flags):
    generator, repository, _, _ = make_generator()

    with pytest.raises(SafariEncounterGenerationError, match="already seen"):
        await getattr(generator, method_name)(make_context(extraordinary_flags=flags))

    assert repository.get_all_calls == 0


@pytest.mark.asyncio
async def test_extraordinary_flags_are_independent():
    catalog = (
        make_species(1, legendary=True),
        make_species(2, mythical=True),
    )
    generator, _, _, _ = make_generator(catalog)

    mythical = await generator.generate_mythical(
        make_context(extraordinary_flags=SafariExtraordinaryFlags(legendary_seen=True))
    )
    legendary = await generator.generate_legendary(
        make_context(extraordinary_flags=SafariExtraordinaryFlags(mythical_seen=True))
    )

    assert mythical.encounter.composition == SafariComposition.MYTHICAL
    assert legendary.encounter.composition == SafariComposition.LEGENDARY


@pytest.mark.asyncio
async def test_extraordinary_fallback_skips_a_consumed_category():
    mythical = make_species(2, mythical=True)
    generator, _, _, _ = make_generator((mythical,))
    context = make_context(
        extraordinary_flags=SafariExtraordinaryFlags(legendary_seen=True)
    )

    result = await generator.generate_extraordinary_with_events(
        context,
        (SafariComposition.LEGENDARY, SafariComposition.MYTHICAL),
    )

    assert result.encounter.composition == SafariComposition.MYTHICAL


@pytest.mark.asyncio
async def test_event_filters_extraordinary_types_without_extra_weight():
    fire_rock = make_species(1, types=["fire", "rock"], legendary=True)
    neutral = make_species(2, types=["normal"], legendary=True)
    random_source = ScriptedRandom(species_ids=(1,))
    generator, _, _, _ = make_generator(
        (fire_rock, neutral),
        random_source=random_source,
    )
    context = make_context(
        safari_map=SafariMap.MOUNTAIN,
        zone=SafariZone.ROCKY_SLOPE,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.VOLCANIC_ACTIVITY}
        ),
    )

    result = await generator.generate_legendary(
        context,
        SafariThematicEvent.VOLCANIC_ACTIVITY,
    )
    _, weights = random_source.species_calls[0]
    base_weight = RARITY_CONFIG[Rarity.COMMON].spawn_weight

    assert result.event == SafariThematicEvent.VOLCANIC_ACTIVITY
    assert weights == (base_weight,)


@pytest.mark.asyncio
async def test_event_without_candidates_can_fall_through_to_none():
    fire_legendary = make_species(1, types=["fire"], legendary=True)
    random_source = ScriptedRandom(
        event_order=(SafariThematicEvent.FISHING, SafariThematicEvent.NONE)
    )
    generator, _, _, _ = make_generator(
        (fire_legendary,),
        random_source=random_source,
    )
    context = make_context(
        zone=SafariZone.RIVERBANK,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.FISHING}
        ),
    )

    result = await generator.generate_extraordinary_with_events(
        context,
        (SafariComposition.LEGENDARY,),
    )

    assert result.event == SafariThematicEvent.NONE
    assert [len(call[0]) for call in random_source.event_calls] == [2, 1]


@pytest.mark.asyncio
async def test_extraordinary_fallback_tries_another_category_without_normal():
    mythical = make_species(2, mythical=True)
    generator, _, _, _ = make_generator((mythical,))

    result = await generator.generate_extraordinary_with_events(
        make_context(),
        (SafariComposition.LEGENDARY, SafariComposition.MYTHICAL),
    )

    assert result.encounter.composition == SafariComposition.MYTHICAL


@pytest.mark.asyncio
async def test_extraordinary_fallback_never_degrades_to_normal():
    generator, _, factory, _ = make_generator((make_species(1),))

    with pytest.raises(SafariEncounterGenerationError, match="extraordinary"):
        await generator.generate_extraordinary_with_events(
            make_context(),
            (SafariComposition.LEGENDARY, SafariComposition.MYTHICAL),
        )

    assert factory.calls == []


@pytest.mark.asyncio
async def test_common_apis_still_exclude_legendary_and_mythical():
    catalog = (
        make_species(1, legendary=True),
        make_species(2, mythical=True),
        make_species(3),
    )
    generator, _, _, _ = make_generator(catalog)

    encounter = await generator.generate(make_context(), SafariComposition.NORMAL)

    assert {slot.species_id for slot in encounter.slots} == {3}


@pytest.mark.parametrize("phase", [SafariPhase.START, SafariPhase.DEVELOPMENT])
def test_global_shiny_is_rejected_before_final(phase):
    generator, _, _, _ = make_generator()

    with pytest.raises(SafariEncounterGenerationError, match="FINAL"):
        generator.apply_global_shiny(make_context(phase=phase), make_encounter())


def test_global_shiny_flag_blocks_second_global_shiny():
    generator, _, _, _ = make_generator()
    flags = SafariExtraordinaryFlags(shiny_encounter_seen=True)

    with pytest.raises(SafariEncounterGenerationError, match="already seen"):
        generator.apply_global_shiny(
            make_context(extraordinary_flags=flags),
            make_encounter(),
        )


@pytest.mark.parametrize(
    "composition",
    [
        SafariComposition.NORMAL,
        SafariComposition.DUEL,
        SafariComposition.HERD,
        SafariComposition.SOLITARY,
        SafariComposition.BABY_NEST,
        SafariComposition.REGIONAL,
        SafariComposition.LEGENDARY,
        SafariComposition.MYTHICAL,
    ],
)
def test_global_shiny_preserves_encounter_and_opportunity_attributes(composition):
    factory = RecordingOpportunityFactory()
    generator, _, _, _ = make_generator(factory=factory)
    original = make_encounter(
        composition,
        regional_herd=composition == SafariComposition.REGIONAL,
    )
    original_values = tuple(
        (
            slot.id,
            slot.opportunity.species,
            slot.opportunity.ivs,
            slot.opportunity.nature,
            slot.opportunity.size,
            slot.opportunity.initial_form,
            slot.opportunity.failed_attempts,
        )
        for slot in original.slots
    )
    original_shiny_values = tuple(slot.opportunity.is_shiny for slot in original.slots)

    shiny = generator.apply_global_shiny(make_context(), original)

    assert isinstance(shiny, SafariEncounter)
    assert shiny is not original
    assert shiny.id == original.id
    assert shiny.composition == original.composition
    assert shiny.is_regional_herd == original.is_regional_herd
    assert all(slot.opportunity.is_shiny for slot in shiny.slots)
    assert (
        tuple(slot.opportunity.is_shiny for slot in original.slots)
        == original_shiny_values
    )
    assert (
        tuple(
            (
                slot.id,
                slot.opportunity.species,
                slot.opportunity.ivs,
                slot.opportunity.nature,
                slot.opportunity.size,
                slot.opportunity.initial_form,
                slot.opportunity.failed_attempts,
            )
            for slot in shiny.slots
        )
        == original_values
    )
    assert factory.calls == []


def test_global_shiny_preserves_generated_event_and_regional_form():
    generator, _, _, _ = make_generator()
    encounter = make_encounter(SafariComposition.REGIONAL, regional_herd=True)
    generated = SafariGeneratedRegionalEncounter(
        encounter,
        SafariThematicEvent.RAINBOW,
        SafariRegionalEncounterForm.HERD,
    )

    shiny = generator.apply_global_shiny(make_context(), generated)

    assert isinstance(shiny, SafariGeneratedRegionalEncounter)
    assert shiny.event == SafariThematicEvent.RAINBOW
    assert shiny.regional_form == SafariRegionalEncounterForm.HERD
    assert shiny.encounter.is_regional_herd
    assert all(slot.opportunity.is_shiny for slot in shiny.encounter.slots)
    assert all(
        slot.capture_policy is SafariCapturePolicy.UNIQUE
        for slot in shiny.encounter.slots
    )


def test_global_shiny_preserves_common_generated_event():
    generator, _, _, _ = make_generator()
    generated = SafariGeneratedEncounter(
        make_encounter(SafariComposition.LEGENDARY, slot_count=1),
        SafariThematicEvent.VOLCANIC_ACTIVITY,
    )

    shiny = generator.apply_global_shiny(make_context(), generated)

    assert isinstance(shiny, SafariGeneratedEncounter)
    assert shiny.event == SafariThematicEvent.VOLCANIC_ACTIVITY
    assert shiny.encounter.composition == SafariComposition.LEGENDARY
    assert shiny.encounter.slots[0].opportunity.is_shiny


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "composition", "species"),
    [
        (
            "generate_legendary",
            SafariComposition.LEGENDARY,
            make_species(1, legendary=True),
        ),
        (
            "generate_mythical",
            SafariComposition.MYTHICAL,
            make_species(2, mythical=True),
        ),
    ],
)
async def test_generated_legendary_and_mythical_can_become_global_shiny(
    method_name,
    composition,
    species,
):
    generator, _, factory, _ = make_generator((species,))
    generated = await getattr(generator, method_name)(make_context())
    calls_before_shiny = len(factory.calls)

    shiny = generator.apply_global_shiny(make_context(), generated)

    assert isinstance(shiny, SafariGeneratedEncounter)
    assert shiny.encounter.composition == composition
    assert shiny.encounter.slots[0].opportunity.is_shiny
    assert len(factory.calls) == calls_before_shiny


def test_global_shiny_keeps_slots_that_were_already_shiny():
    generator, _, _, _ = make_generator()
    encounter = make_encounter()
    encounter.slots[0].opportunity.is_shiny = True

    shiny = generator.apply_global_shiny(make_context(), encounter)

    assert all(slot.opportunity.is_shiny for slot in shiny.slots)
    assert encounter.slots[0].opportunity.is_shiny


def test_global_shiny_cannot_modify_a_published_encounter():
    generator, _, _, _ = make_generator()
    encounter = make_encounter()
    encounter._set_eligible_participant_ids(frozenset({1}))

    with pytest.raises(SafariEncounterGenerationError, match="before publishing"):
        generator.apply_global_shiny(make_context(), encounter)
