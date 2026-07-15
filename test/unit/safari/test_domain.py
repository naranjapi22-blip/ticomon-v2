from collections import deque
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from core.safari import (
    SAFARI_INITIAL_ZONE_BY_MAP,
    SAFARI_LEVEL_CONFIGS,
    SAFARI_MIN_PARTICIPANTS,
    SAFARI_VALID_WEATHER_BY_MAP,
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SAFARI_ZONE_DEFINITIONS,
    TIME_OF_DAY_WEIGHTS,
    WEATHER_WEIGHTS,
    SafariCapturePolicy,
    SafariComposition,
    SafariEncounterStatus,
    SafariExtraordinaryFlags,
    SafariFinishReason,
    SafariLevelConfiguration,
    SafariMap,
    SafariMapInfluence,
    SafariPhase,
    SafariRegistrationStatus,
    SafariRouteVoteStatus,
    SafariSessionStatus,
    SafariSlotStatus,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariUnlockStatus,
    SafariWeather,
    SafariZone,
    SafariZoneDefinition,
)


def test_global_participant_policy_is_canonical():
    assert SAFARI_MIN_PARTICIPANTS == 2


def test_enum_values_are_exact():
    assert [member.value for member in SafariMap] == [
        "FOREST",
        "MOUNTAIN",
        "COAST",
        "SWAMP",
        "PLAINS",
    ]
    assert [member.value for member in SafariWeather] == [
        "CLEAR",
        "RAIN",
        "FOG",
        "STORM",
        "SNOW",
    ]
    assert [member.value for member in SafariTimeOfDay] == [
        "DAY",
        "SUNSET",
        "NIGHT",
    ]
    assert [member.value for member in SafariPhase] == [
        "START",
        "DEVELOPMENT",
        "FINAL",
    ]
    assert [member.value for member in SafariRegistrationStatus] == [
        "OPEN",
        "CANCELLED",
        "CONSUMED",
    ]
    assert [member.value for member in SafariSessionStatus] == [
        "ENCOUNTER",
        "ROUTE_DECISION",
        "RESOLUTION",
        "FINISHED",
        "CANCELLED",
    ]
    assert [member.value for member in SafariEncounterStatus] == [
        "OPEN",
        "RESOLVING",
        "RESOLVED",
    ]
    assert [member.value for member in SafariSlotStatus] == [
        "AVAILABLE",
        "CAPTURED",
        "ESCAPED",
    ]
    assert [member.value for member in SafariCapturePolicy] == [
        "SHARED",
        "UNIQUE",
    ]
    assert [member.value for member in SafariRouteVoteStatus] == [
        "OPEN",
        "RESOLVED",
        "CANCELLED",
    ]
    assert [member.value for member in SafariComposition] == [
        "NORMAL",
        "DUEL",
        "HERD",
        "SOLITARY",
        "BABY_NEST",
        "REGIONAL",
        "LEGENDARY",
        "MYTHICAL",
    ]
    assert [member.value for member in SafariThematicEvent] == [
        "NONE",
        "VOLCANIC_ACTIVITY",
        "FISHING",
        "MIGRATION",
        "DISTORTION",
        "DEPOSIT",
        "GRAVEYARD",
        "ANCIENT_RUINS",
        "RAINBOW",
        "DEN",
        "NEST",
    ]
    assert [member.value for member in SafariUnlockStatus] == [
        "AVAILABLE",
        "EXPIRED",
        "CONSUMED",
    ]
    assert [member.value for member in SafariFinishReason] == [
        "COMPLETED",
        "NO_BALLS_REMAINING",
        "ADMINISTRATIVE_ABORT",
    ]


def test_level_configs_are_exact_and_positive():
    assert set(SAFARI_LEVEL_CONFIGS) == {1, 2, 3, 4, 5}

    assert SAFARI_LEVEL_CONFIGS[1] == SafariLevelConfiguration(
        level=1,
        encounter_count=5,
        balls_per_participant=9,
        decision_count=2,
    )
    assert SAFARI_LEVEL_CONFIGS[2] == SafariLevelConfiguration(
        level=2,
        encounter_count=7,
        balls_per_participant=12,
        decision_count=2,
    )
    assert SAFARI_LEVEL_CONFIGS[3] == SafariLevelConfiguration(
        level=3,
        encounter_count=9,
        balls_per_participant=15,
        decision_count=3,
    )
    assert SAFARI_LEVEL_CONFIGS[4] == SafariLevelConfiguration(
        level=4,
        encounter_count=11,
        balls_per_participant=18,
        decision_count=3,
    )
    assert SAFARI_LEVEL_CONFIGS[5] == SafariLevelConfiguration(
        level=5,
        encounter_count=13,
        balls_per_participant=21,
        decision_count=4,
    )

    assert all(
        value > 0
        for config in SAFARI_LEVEL_CONFIGS.values()
        for value in (
            config.level,
            config.encounter_count,
            config.balls_per_participant,
            config.decision_count,
        )
    )


def test_zone_definitions_cover_all_zones_once():
    defined_zones = [definition.zone for definition in SAFARI_ZONE_DEFINITIONS]

    assert len(defined_zones) == len(set(defined_zones))
    assert set(defined_zones) == set(SafariZone)
    assert set(SAFARI_ZONE_DEFINITION_BY_ZONE) == set(SafariZone)


def test_each_map_has_an_initial_zone_and_it_belongs_to_that_map():
    assert set(SAFARI_INITIAL_ZONE_BY_MAP) == set(SafariMap)

    for safari_map, zone in SAFARI_INITIAL_ZONE_BY_MAP.items():
        definition = SAFARI_ZONE_DEFINITION_BY_ZONE[zone]

        assert definition.safari_map == safari_map


def test_zone_transitions_stay_inside_the_same_map_and_are_reachable():
    for definition in SAFARI_ZONE_DEFINITIONS:
        assert definition.allowed_events
        assert SafariThematicEvent.NONE in definition.allowed_events
        assert definition.transitions

        for transition in definition.transitions:
            assert transition in SAFARI_ZONE_DEFINITION_BY_ZONE
            assert (
                SAFARI_ZONE_DEFINITION_BY_ZONE[transition].safari_map
                == definition.safari_map
            )

    for safari_map, initial_zone in SAFARI_INITIAL_ZONE_BY_MAP.items():
        reachable: set[SafariZone] = set()
        queue: deque[SafariZone] = deque([initial_zone])

        while queue:
            zone = queue.popleft()
            if zone in reachable:
                continue

            reachable.add(zone)
            queue.extend(
                transition
                for transition in SAFARI_ZONE_DEFINITION_BY_ZONE[zone].transitions
                if transition not in reachable
            )

        map_zones = {
            definition.zone
            for definition in SAFARI_ZONE_DEFINITIONS
            if definition.safari_map == safari_map
        }

        assert reachable == map_zones


def test_corrected_zones_include_all_agreed_affinities():
    expected_types = {
        SafariZone.DEEP_FOREST: {"grass", "bug", "poison", "ghost"},
        SafariZone.CLEARING: {"normal", "flying", "fairy", "grass"},
        SafariZone.MARSH_EDGE: {"water", "poison", "bug", "ground"},
        SafariZone.DEEP_CAVE: {"rock", "dark", "ghost", "steel"},
    }

    for zone, expected in expected_types.items():
        weights = SAFARI_ZONE_DEFINITION_BY_ZONE[zone].base_type_weights

        assert set(weights) == expected
        assert all(weight > 0 for weight in weights.values())


def test_weather_configuration_is_valid_for_each_map():
    assert set(SAFARI_VALID_WEATHER_BY_MAP) == set(SafariMap)

    for safari_map, weather_values in SAFARI_VALID_WEATHER_BY_MAP.items():
        assert weather_values
        assert SafariWeather.CLEAR in weather_values
        assert set(weather_values).issubset(set(SafariWeather))
        if safari_map != SafariMap.MOUNTAIN:
            assert SafariWeather.SNOW not in weather_values

    assert WEATHER_WEIGHTS == {
        SafariWeather.CLEAR: 50,
        SafariWeather.RAIN: 20,
        SafariWeather.FOG: 15,
        SafariWeather.STORM: 10,
        SafariWeather.SNOW: 5,
    }

    assert TIME_OF_DAY_WEIGHTS == {
        SafariTimeOfDay.DAY: 50,
        SafariTimeOfDay.SUNSET: 20,
        SafariTimeOfDay.NIGHT: 30,
    }


def test_map_influence_rejects_negative_values_and_reports_values():
    influence = SafariMapInfluence({"grass": 3})

    assert influence.get("grass") == 3
    assert influence.get("poison") == 0
    assert not influence.is_empty()

    empty = SafariMapInfluence()
    assert empty.is_empty()
    assert empty.get("grass") == 0

    with pytest.raises(ValueError):
        SafariMapInfluence({"grass": -1})

    source = {"grass": 2}
    influence = SafariMapInfluence(source)
    source["grass"] = 9

    assert influence.get("grass") == 2
    assert isinstance(influence.amounts, MappingProxyType)


def test_level_configuration_rejects_non_positive_values():
    with pytest.raises(ValueError):
        SafariLevelConfiguration(
            level=0,
            encounter_count=5,
            balls_per_participant=9,
            decision_count=2,
        )

    with pytest.raises(ValueError):
        SafariLevelConfiguration(
            level=1,
            encounter_count=-1,
            balls_per_participant=9,
            decision_count=2,
        )


def test_zone_definition_is_immutable_and_keeps_data_as_tuples():
    definition = SAFARI_ZONE_DEFINITION_BY_ZONE[SafariZone.FOREST_ENTRANCE]

    assert isinstance(definition, SafariZoneDefinition)
    assert isinstance(definition.base_type_weights, MappingProxyType)
    assert isinstance(definition.allowed_events, tuple)
    assert isinstance(definition.transitions, tuple)

    with pytest.raises(FrozenInstanceError):
        definition.zone = SafariZone.CLEARING  # type: ignore[misc]

    with pytest.raises(TypeError):
        definition.base_type_weights["normal"] = 2.0  # type: ignore[index]

    with pytest.raises(ValueError):
        SafariZoneDefinition(
            zone=SafariZone.CLEARING,
            safari_map=SafariMap.FOREST,
            base_type_weights={"normal": 0.0},
            allowed_events=(SafariThematicEvent.NONE,),
            transitions=(SafariZone.FOREST_ENTRANCE,),
        )

    with pytest.raises(ValueError):
        SafariZoneDefinition(
            zone=SafariZone.CLEARING,
            safari_map=SafariMap.FOREST,
            base_type_weights={"normal": -1.0},
            allowed_events=(SafariThematicEvent.NONE,),
            transitions=(SafariZone.FOREST_ENTRANCE,),
        )


def test_extraordinary_flags_start_false():
    flags = SafariExtraordinaryFlags()

    assert flags == SafariExtraordinaryFlags(
        legendary_seen=False,
        mythical_seen=False,
        shiny_encounter_seen=False,
        regional_herd_seen=False,
    )
