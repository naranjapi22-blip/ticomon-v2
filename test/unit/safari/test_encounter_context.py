from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from core.safari import (
    SafariEncounterContext,
    SafariExtraordinaryFlags,
    SafariMap,
    SafariPhase,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)


def make_context(**overrides) -> SafariEncounterContext:
    values = {
        "safari_map": SafariMap.FOREST,
        "zone": SafariZone.FOREST_ENTRANCE,
        "weather": SafariWeather.CLEAR,
        "time_of_day": SafariTimeOfDay.DAY,
        "phase": SafariPhase.START,
        "map_type_weight_modifiers": {"grass": 1.2},
        "zone_type_weight_modifiers": {"bug": 1.5},
        "route_type_weight_modifiers": {"normal": 1.1},
        "seen_species_ids": {1, 2},
    }
    values.update(overrides)
    return SafariEncounterContext(**values)


def test_context_is_valid_immutable_and_copies_collections():
    map_modifiers = {"grass": 1.2}
    seen_species_ids = {1, 2}
    context = make_context(
        map_type_weight_modifiers=map_modifiers,
        seen_species_ids=seen_species_ids,
    )
    map_modifiers["grass"] = 9.0
    seen_species_ids.add(3)

    assert context.map_type_weight_modifiers["grass"] == 1.2
    assert isinstance(context.map_type_weight_modifiers, MappingProxyType)
    assert context.seen_species_ids == frozenset({1, 2})
    with pytest.raises(TypeError):
        context.map_type_weight_modifiers["grass"] = 2.0  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        context.weather = SafariWeather.RAIN  # type: ignore[misc]


def test_context_preserves_weather_and_time_without_deriving_modifiers():
    context = make_context(
        weather=SafariWeather.RAIN,
        time_of_day=SafariTimeOfDay.NIGHT,
    )

    assert context.weather == SafariWeather.RAIN
    assert context.time_of_day == SafariTimeOfDay.NIGHT


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("safari_map", "FOREST"),
        ("zone", "FOREST_ENTRANCE"),
        ("weather", "CLEAR"),
        ("time_of_day", "DAY"),
        ("phase", "START"),
    ],
)
def test_context_requires_domain_enums(field_name, invalid_value):
    with pytest.raises(ValueError):
        make_context(**{field_name: invalid_value})


def test_context_rejects_zone_or_weather_outside_map():
    with pytest.raises(ValueError, match="zone"):
        make_context(zone=SafariZone.COAST_SHORE)
    with pytest.raises(ValueError, match="weather"):
        make_context(weather=SafariWeather.SNOW)


@pytest.mark.parametrize("seen_species_ids", [{0}, {-1}])
def test_context_rejects_non_positive_seen_species_ids(seen_species_ids):
    with pytest.raises(ValueError, match="positive"):
        make_context(seen_species_ids=seen_species_ids)


@pytest.mark.parametrize(
    "modifiers",
    [{"Fire": 1.2}, {" fire": 1.2}, {"fire": -0.1}],
)
def test_context_rejects_noncanonical_or_negative_modifiers(modifiers):
    with pytest.raises(ValueError):
        make_context(map_type_weight_modifiers=modifiers)


def test_context_allows_explicit_zero_modifier():
    context = make_context(route_type_weight_modifiers={"fire": 0.0})

    assert context.route_type_weight_modifiers["fire"] == 0.0


def test_context_preserves_immutable_extraordinary_flags():
    flags = SafariExtraordinaryFlags(legendary_seen=True)

    context = make_context(extraordinary_flags=flags)

    assert context.extraordinary_flags is flags
    with pytest.raises(FrozenInstanceError):
        context.extraordinary_flags.legendary_seen = False  # type: ignore[misc]


def test_context_rejects_invalid_extraordinary_flags():
    with pytest.raises(ValueError, match="extraordinary_flags"):
        make_context(extraordinary_flags=None)
