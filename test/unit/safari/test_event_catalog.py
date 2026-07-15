from types import MappingProxyType

import pytest

from core.safari import (
    COMMON_SAFARI_COMPOSITIONS,
    EVENT_COMPOSITION_COMPATIBILITY,
    EVENT_REQUIRED_TYPES,
    EVENT_WEIGHTS,
    EVENTS_BY_PHASE,
    EVENTS_BY_ZONE,
    EXTRAORDINARY_SAFARI_COMPOSITIONS,
    SafariComposition,
    SafariEncounterContext,
    SafariMap,
    SafariPhase,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
    available_events_for,
    available_extraordinary_events_for,
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


def test_event_required_types_are_complete_canonical_and_immutable():
    assert isinstance(EVENT_REQUIRED_TYPES, MappingProxyType)
    assert set(EVENT_REQUIRED_TYPES) == set(SafariThematicEvent)
    assert all(
        all(name == name.strip().lower() for name in required_types)
        for required_types in EVENT_REQUIRED_TYPES.values()
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.NONE] == frozenset()
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.VOLCANIC_ACTIVITY] == frozenset(
        {"fire", "rock"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.FISHING] == frozenset({"water"})
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.MIGRATION] == frozenset(
        {"flying", "normal"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.DISTORTION] == frozenset(
        {"psychic", "ghost"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.DEPOSIT] == frozenset(
        {"rock", "ground", "steel"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.GRAVEYARD] == frozenset(
        {"ghost", "dark"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.ANCIENT_RUINS] == frozenset(
        {"rock", "psychic", "ghost"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.RAINBOW] == frozenset(
        {"fairy", "flying"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.DEN] == frozenset(
        {"dragon", "dark", "fighting"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.NEST] == frozenset(
        {"bug", "flying", "grass"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.THUNDERSTORM] == frozenset(
        {"electric"}
    )
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.BLIZZARD] == frozenset({"ice"})
    assert EVENT_REQUIRED_TYPES[SafariThematicEvent.TOXIC_BLOOM] == frozenset(
        {"poison"}
    )
    with pytest.raises(TypeError):
        EVENT_REQUIRED_TYPES[SafariThematicEvent.FISHING] = frozenset()  # type: ignore[index]


def test_compatibility_contains_only_supported_compositions():
    assert isinstance(EVENT_COMPOSITION_COMPATIBILITY, MappingProxyType)
    assert set(EVENT_COMPOSITION_COMPATIBILITY) == set(SafariThematicEvent)
    assert (
        EVENT_COMPOSITION_COMPATIBILITY[SafariThematicEvent.NONE]
        == COMMON_SAFARI_COMPOSITIONS | EXTRAORDINARY_SAFARI_COMPOSITIONS
    )
    assert all(
        compositions <= COMMON_SAFARI_COMPOSITIONS | EXTRAORDINARY_SAFARI_COMPOSITIONS
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


def test_new_events_have_exact_zones_phases_compositions_and_type_coverage():
    expected_zones = {
        SafariThematicEvent.THUNDERSTORM: {
            SafariZone.SUMMIT,
            SafariZone.OPEN_FIELD,
            SafariZone.COAST_SHORE,
        },
        SafariThematicEvent.BLIZZARD: {
            SafariZone.SUMMIT,
            SafariZone.ROCKY_SLOPE,
        },
        SafariThematicEvent.TOXIC_BLOOM: {
            SafariZone.DEAD_FOREST,
            SafariZone.DENSE_REEDS,
            SafariZone.DEEP_MARSH,
        },
    }
    expected_compositions = frozenset(
        {
            SafariComposition.NORMAL,
            SafariComposition.DUEL,
            SafariComposition.HERD,
        }
    )
    for event, zones in expected_zones.items():
        assert {
            zone for zone, events in EVENTS_BY_ZONE.items() if event in events
        } == zones
        assert event not in EVENTS_BY_PHASE[SafariPhase.START]
        assert event in EVENTS_BY_PHASE[SafariPhase.DEVELOPMENT]
        assert event in EVENTS_BY_PHASE[SafariPhase.FINAL]
        assert EVENT_COMPOSITION_COMPATIBILITY[event] == expected_compositions

    covered_types = set().union(*EVENT_REQUIRED_TYPES.values())
    assert covered_types == {
        "bug",
        "dark",
        "dragon",
        "electric",
        "fairy",
        "fighting",
        "fire",
        "flying",
        "ghost",
        "grass",
        "ground",
        "ice",
        "normal",
        "poison",
        "psychic",
        "rock",
        "steel",
        "water",
    }
    assert EVENT_WEIGHTS[SafariThematicEvent.THUNDERSTORM] == 6.0
    assert EVENT_WEIGHTS[SafariThematicEvent.BLIZZARD] == 5.0
    assert EVENT_WEIGHTS[SafariThematicEvent.TOXIC_BLOOM] == 6.0
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


def test_extraordinary_availability_uses_explicit_compatibility():
    context = make_context(phase=SafariPhase.FINAL)

    events = available_extraordinary_events_for(
        context,
        SafariComposition.LEGENDARY,
    )

    assert events == frozenset({SafariThematicEvent.NONE, SafariThematicEvent.FISHING})
    with pytest.raises(ValueError, match="extraordinary"):
        available_extraordinary_events_for(context, SafariComposition.NORMAL)


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
