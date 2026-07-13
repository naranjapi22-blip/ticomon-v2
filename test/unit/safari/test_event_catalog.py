from types import MappingProxyType

import pytest

from core.safari import (
    COMMON_SAFARI_COMPOSITIONS,
    EVENT_COMPOSITION_COMPATIBILITY,
    EVENT_REQUIRED_TYPES,
    EVENT_TYPE_MODIFIERS,
    EVENT_WEIGHTS,
    EVENTS_BY_PHASE,
    EVENTS_BY_ZONE,
    SafariComposition,
    SafariEncounterContext,
    SafariMap,
    SafariPhase,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
    available_events_for,
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


def test_event_configuration_is_complete_positive_and_immutable():
    assert isinstance(EVENT_WEIGHTS, MappingProxyType)
    assert set(EVENT_WEIGHTS) == set(SafariThematicEvent)
    assert all(weight > 0 for weight in EVENT_WEIGHTS.values())
    assert EVENT_WEIGHTS[SafariThematicEvent.NONE] == max(EVENT_WEIGHTS.values())
    with pytest.raises(TypeError):
        EVENT_WEIGHTS[SafariThematicEvent.NONE] = 1.0  # type: ignore[index]


def test_event_type_modifiers_are_canonical_non_negative_and_deeply_immutable():
    assert isinstance(EVENT_TYPE_MODIFIERS, MappingProxyType)
    assert set(EVENT_TYPE_MODIFIERS) == set(SafariThematicEvent)
    for modifiers in EVENT_TYPE_MODIFIERS.values():
        assert isinstance(modifiers, MappingProxyType)
        assert all(name == name.strip().lower() for name in modifiers)
        assert all(value >= 0 for value in modifiers.values())
    assert EVENT_TYPE_MODIFIERS[SafariThematicEvent.NONE] == {}
    with pytest.raises(TypeError):
        EVENT_TYPE_MODIFIERS[SafariThematicEvent.FISHING]["water"] = 2.0  # type: ignore[index]


def test_compatibility_contains_only_common_compositions():
    assert isinstance(EVENT_COMPOSITION_COMPATIBILITY, MappingProxyType)
    assert set(EVENT_COMPOSITION_COMPATIBILITY) == set(SafariThematicEvent)
    assert (
        EVENT_COMPOSITION_COMPATIBILITY[SafariThematicEvent.NONE]
        == COMMON_SAFARI_COMPOSITIONS
    )
    assert all(
        compositions <= COMMON_SAFARI_COMPOSITIONS
        for compositions in EVENT_COMPOSITION_COMPATIBILITY.values()
    )
    with pytest.raises(TypeError):
        EVENT_COMPOSITION_COMPATIBILITY[SafariThematicEvent.NONE] = frozenset()  # type: ignore[index]


def test_zone_and_phase_catalogs_are_complete_and_always_include_none():
    assert isinstance(EVENTS_BY_ZONE, MappingProxyType)
    assert isinstance(EVENTS_BY_PHASE, MappingProxyType)
    assert set(EVENTS_BY_ZONE) == set(SafariZone)
    assert all(SafariThematicEvent.NONE in events for events in EVENTS_BY_ZONE.values())
    assert set().union(*EVENTS_BY_ZONE.values()) == set(SafariThematicEvent)
    assert set(EVENTS_BY_PHASE) == set(SafariPhase)
    assert all(
        SafariThematicEvent.NONE in events for events in EVENTS_BY_PHASE.values()
    )
    assert all(isinstance(events, frozenset) for events in EVENTS_BY_ZONE.values())
    assert all(isinstance(events, frozenset) for events in EVENTS_BY_PHASE.values())


def test_required_type_filters_are_declarative_and_complete():
    assert set(EVENT_REQUIRED_TYPES) == set(SafariThematicEvent)
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.FISHING] == frozenset({"water"})
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.NONE] == frozenset()


def test_contextual_availability_intersects_zone_route_phase_and_composition():
    events = available_events_for(make_context(), SafariComposition.NORMAL)
    assert events == frozenset({SafariThematicEvent.NONE, SafariThematicEvent.FISHING})

    route_limited = make_context(
        route_allowed_events=frozenset({SafariThematicEvent.NONE})
    )
    assert available_events_for(route_limited, SafariComposition.NORMAL) == frozenset(
        {SafariThematicEvent.NONE}
    )


def test_invalid_zone_event_and_incompatible_composition_are_excluded():
    context = make_context()
    assert SafariThematicEvent.DEPOSIT not in available_events_for(
        context,
        SafariComposition.NORMAL,
    )
    assert SafariThematicEvent.FISHING not in available_events_for(
        context,
        SafariComposition.BABY_NEST,
    )


def test_phase_can_block_an_event_and_none_remains_available():
    context = make_context(
        safari_map=SafariMap.MOUNTAIN,
        zone=SafariZone.DEEP_CAVE,
        phase=SafariPhase.START,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.DISTORTION}
        ),
    )

    assert available_events_for(context, SafariComposition.NORMAL) == frozenset(
        {SafariThematicEvent.NONE}
    )


def test_den_is_available_only_for_compatible_compositions():
    context = make_context(
        safari_map=SafariMap.MOUNTAIN,
        zone=SafariZone.CAVE_ENTRANCE,
        phase=SafariPhase.DEVELOPMENT,
        route_allowed_events=frozenset(
            {SafariThematicEvent.NONE, SafariThematicEvent.DEN}
        ),
    )

    assert SafariThematicEvent.DEN not in available_events_for(
        context,
        SafariComposition.NORMAL,
    )
    assert SafariThematicEvent.DEN in available_events_for(
        context,
        SafariComposition.HERD,
    )


def test_context_defaults_route_events_to_zone_events_and_freezes_input():
    context = make_context(route_allowed_events=None)
    assert context.route_allowed_events == EVENTS_BY_ZONE[SafariZone.RIVERBANK]

    events = {SafariThematicEvent.NONE, SafariThematicEvent.FISHING}
    context = make_context(route_allowed_events=events)
    events.clear()
    assert context.route_allowed_events == frozenset(
        {SafariThematicEvent.NONE, SafariThematicEvent.FISHING}
    )


def test_route_events_require_none():
    with pytest.raises(ValueError, match="include NONE"):
        make_context(route_allowed_events=frozenset({SafariThematicEvent.FISHING}))
