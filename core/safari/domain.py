from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class SafariMap(str, Enum):
    FOREST = "FOREST"
    MOUNTAIN = "MOUNTAIN"
    COAST = "COAST"
    SWAMP = "SWAMP"
    PLAINS = "PLAINS"


class SafariZone(str, Enum):
    FOREST_ENTRANCE = "FOREST_ENTRANCE"
    DEEP_FOREST = "DEEP_FOREST"
    RIVERBANK = "RIVERBANK"
    CLEARING = "CLEARING"
    ANCIENT_GROVE = "ANCIENT_GROVE"
    MARSH_EDGE = "MARSH_EDGE"
    HILLSIDE_PATH = "HILLSIDE_PATH"
    MOUNTAIN_FOOTHILL = "MOUNTAIN_FOOTHILL"
    ROCKY_SLOPE = "ROCKY_SLOPE"
    VALLEY = "VALLEY"
    CAVE_ENTRANCE = "CAVE_ENTRANCE"
    DEEP_CAVE = "DEEP_CAVE"
    HIGH_RIDGE = "HIGH_RIDGE"
    FROZEN_PASS = "FROZEN_PASS"
    UNDERGROUND_LAKE = "UNDERGROUND_LAKE"
    SUMMIT = "SUMMIT"
    COAST_SHORE = "COAST_SHORE"
    ROCKY_BEACH = "ROCKY_BEACH"
    TIDAL_POOLS = "TIDAL_POOLS"
    COASTAL_PATH = "COASTAL_PATH"
    SEA_CAVE = "SEA_CAVE"
    CLIFFSIDE = "CLIFFSIDE"
    LAGOON = "LAGOON"
    MANGROVE_EDGE = "MANGROVE_EDGE"
    DUNES = "DUNES"
    SWAMP_EDGE = "SWAMP_EDGE"
    MUDDY_TRAIL = "MUDDY_TRAIL"
    SHALLOW_WATER = "SHALLOW_WATER"
    DENSE_REEDS = "DENSE_REEDS"
    DEAD_FOREST = "DEAD_FOREST"
    DEEP_MARSH = "DEEP_MARSH"
    MISTY_CLEARING = "MISTY_CLEARING"
    NESTING_GROUND = "NESTING_GROUND"
    PLAINS_TRAIL = "PLAINS_TRAIL"
    OPEN_FIELD = "OPEN_FIELD"
    TALL_GRASS = "TALL_GRASS"
    LOW_HILLS = "LOW_HILLS"
    FLOWER_MEADOW = "FLOWER_MEADOW"
    WINDY_FIELD = "WINDY_FIELD"
    RIVER_CROSSING = "RIVER_CROSSING"
    HERDING_GROUNDS = "HERDING_GROUNDS"
    ROCKY_OUTCROP = "ROCKY_OUTCROP"


class SafariWeather(str, Enum):
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    FOG = "FOG"
    STORM = "STORM"
    SNOW = "SNOW"


class SafariTimeOfDay(str, Enum):
    DAY = "DAY"
    SUNSET = "SUNSET"
    NIGHT = "NIGHT"


class SafariPhase(str, Enum):
    START = "START"
    DEVELOPMENT = "DEVELOPMENT"
    FINAL = "FINAL"


class SafariRegistrationStatus(str, Enum):
    OPEN = "OPEN"
    CANCELLED = "CANCELLED"
    CONSUMED = "CONSUMED"


class SafariSessionStatus(str, Enum):
    ENCOUNTER = "ENCOUNTER"
    ROUTE_DECISION = "ROUTE_DECISION"
    RESOLUTION = "RESOLUTION"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class SafariEncounterStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVING = "RESOLVING"
    RESOLVED = "RESOLVED"


class SafariSlotStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    CAPTURED = "CAPTURED"
    ESCAPED = "ESCAPED"


class SafariRouteVoteStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class SafariComposition(str, Enum):
    NORMAL = "NORMAL"
    DUEL = "DUEL"
    HERD = "HERD"
    SOLITARY = "SOLITARY"
    BABY_NEST = "BABY_NEST"
    REGIONAL = "REGIONAL"
    LEGENDARY = "LEGENDARY"
    MYTHICAL = "MYTHICAL"


class SafariThematicEvent(str, Enum):
    NONE = "NONE"
    VOLCANIC_ACTIVITY = "VOLCANIC_ACTIVITY"
    FISHING = "FISHING"
    MIGRATION = "MIGRATION"
    DISTORTION = "DISTORTION"
    DEPOSIT = "DEPOSIT"
    GRAVEYARD = "GRAVEYARD"
    ANCIENT_RUINS = "ANCIENT_RUINS"
    RAINBOW = "RAINBOW"
    DEN = "DEN"
    NEST = "NEST"


class SafariUnlockStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    CONSUMED = "CONSUMED"


class SafariFinishReason(str, Enum):
    COMPLETED = "COMPLETED"
    NO_BALLS_REMAINING = "NO_BALLS_REMAINING"
    ADMINISTRATIVE_ABORT = "ADMINISTRATIVE_ABORT"


@dataclass(frozen=True, slots=True)
class SafariMapInfluence:
    amounts: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized = dict(self.amounts)

        for type_name, amount in normalized.items():
            if amount < 0:
                raise ValueError(
                    f"Influence for {type_name!r} cannot be negative.",
                )

        object.__setattr__(
            self,
            "amounts",
            MappingProxyType(normalized),
        )

    def get(
        self,
        type_name: str,
    ) -> int:
        return self.amounts.get(type_name, 0)

    def is_empty(
        self,
    ) -> bool:
        return len(self.amounts) == 0


@dataclass(frozen=True, slots=True)
class SafariLevelConfiguration:
    level: int
    encounter_count: int
    balls_per_participant: int
    decision_count: int

    def __post_init__(self) -> None:
        for field_name in (
            "level",
            "encounter_count",
            "balls_per_participant",
            "decision_count",
        ):
            if getattr(self, field_name) <= 0:
                raise ValueError(
                    f"{field_name} must be positive.",
                )


@dataclass(frozen=True, slots=True)
class SafariZoneDefinition:
    zone: SafariZone
    safari_map: SafariMap
    base_type_weights: Mapping[str, float]
    allowed_events: tuple[SafariThematicEvent, ...]
    transitions: tuple[SafariZone, ...]

    def __post_init__(self) -> None:
        base_type_weights = dict(self.base_type_weights)

        for type_name, weight in base_type_weights.items():
            if weight <= 0:
                raise ValueError(
                    f"Weight for {type_name!r} must be positive.",
                )

        object.__setattr__(
            self,
            "base_type_weights",
            MappingProxyType(base_type_weights),
        )

        object.__setattr__(
            self,
            "allowed_events",
            tuple(self.allowed_events),
        )
        object.__setattr__(
            self,
            "transitions",
            tuple(self.transitions),
        )


@dataclass(frozen=True, slots=True)
class SafariExtraordinaryFlags:
    legendary_seen: bool = False
    mythical_seen: bool = False
    shiny_encounter_seen: bool = False
    regional_herd_seen: bool = False


def _type_weights(*types: str) -> dict[str, float]:
    weights: dict[str, float] = {}

    for index, type_name in enumerate(types):
        if index == 0:
            weight = 1.5
        elif index == 1:
            weight = 1.2
        else:
            weight = 1.1

        weights[type_name] = weight

    return weights


def _events(*events: SafariThematicEvent) -> tuple[SafariThematicEvent, ...]:
    return (SafariThematicEvent.NONE, *events)


SAFARI_LEVEL_CONFIGS: dict[int, SafariLevelConfiguration] = {
    1: SafariLevelConfiguration(
        level=1,
        encounter_count=5,
        balls_per_participant=9,
        decision_count=2,
    ),
    2: SafariLevelConfiguration(
        level=2,
        encounter_count=7,
        balls_per_participant=12,
        decision_count=2,
    ),
    3: SafariLevelConfiguration(
        level=3,
        encounter_count=9,
        balls_per_participant=15,
        decision_count=3,
    ),
    4: SafariLevelConfiguration(
        level=4,
        encounter_count=11,
        balls_per_participant=18,
        decision_count=3,
    ),
    5: SafariLevelConfiguration(
        level=5,
        encounter_count=13,
        balls_per_participant=21,
        decision_count=4,
    ),
}


SAFARI_INITIAL_ZONE_BY_MAP: dict[SafariMap, SafariZone] = {
    SafariMap.FOREST: SafariZone.FOREST_ENTRANCE,
    SafariMap.MOUNTAIN: SafariZone.MOUNTAIN_FOOTHILL,
    SafariMap.COAST: SafariZone.COAST_SHORE,
    SafariMap.SWAMP: SafariZone.SWAMP_EDGE,
    SafariMap.PLAINS: SafariZone.PLAINS_TRAIL,
}


SAFARI_ZONE_DEFINITIONS: tuple[SafariZoneDefinition, ...] = (
    SafariZoneDefinition(
        zone=SafariZone.FOREST_ENTRANCE,
        safari_map=SafariMap.FOREST,
        base_type_weights=_type_weights("Grass", "Bug", "Normal"),
        allowed_events=_events(),
        transitions=(
            SafariZone.DEEP_FOREST,
            SafariZone.RIVERBANK,
            SafariZone.CLEARING,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.DEEP_FOREST,
        safari_map=SafariMap.FOREST,
        base_type_weights=_type_weights("Grass", "Bug", "Poison", "Ghost"),
        allowed_events=_events(SafariThematicEvent.ANCIENT_RUINS),
        transitions=(
            SafariZone.FOREST_ENTRANCE,
            SafariZone.RIVERBANK,
            SafariZone.ANCIENT_GROVE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.RIVERBANK,
        safari_map=SafariMap.FOREST,
        base_type_weights=_type_weights("Water", "Flying", "Grass"),
        allowed_events=_events(SafariThematicEvent.FISHING),
        transitions=(
            SafariZone.FOREST_ENTRANCE,
            SafariZone.DEEP_FOREST,
            SafariZone.MARSH_EDGE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.CLEARING,
        safari_map=SafariMap.FOREST,
        base_type_weights=_type_weights("Normal", "Flying", "Fairy", "Grass"),
        allowed_events=_events(),
        transitions=(
            SafariZone.FOREST_ENTRANCE,
            SafariZone.ANCIENT_GROVE,
            SafariZone.HILLSIDE_PATH,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.ANCIENT_GROVE,
        safari_map=SafariMap.FOREST,
        base_type_weights=_type_weights("Grass", "Fairy", "Ghost"),
        allowed_events=_events(SafariThematicEvent.ANCIENT_RUINS),
        transitions=(
            SafariZone.DEEP_FOREST,
            SafariZone.CLEARING,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.MARSH_EDGE,
        safari_map=SafariMap.FOREST,
        base_type_weights=_type_weights("Water", "Poison", "Bug", "Ground"),
        allowed_events=_events(),
        transitions=(
            SafariZone.RIVERBANK,
            SafariZone.DEEP_FOREST,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.HILLSIDE_PATH,
        safari_map=SafariMap.FOREST,
        base_type_weights=_type_weights("Rock", "Flying", "Fighting"),
        allowed_events=_events(),
        transitions=(
            SafariZone.CLEARING,
            SafariZone.FOREST_ENTRANCE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.MOUNTAIN_FOOTHILL,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Rock", "Ground", "Fighting"),
        allowed_events=_events(),
        transitions=(
            SafariZone.ROCKY_SLOPE,
            SafariZone.VALLEY,
            SafariZone.CAVE_ENTRANCE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.ROCKY_SLOPE,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Rock", "Ground", "Flying"),
        allowed_events=_events(SafariThematicEvent.DEPOSIT),
        transitions=(
            SafariZone.MOUNTAIN_FOOTHILL,
            SafariZone.HIGH_RIDGE,
            SafariZone.CAVE_ENTRANCE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.VALLEY,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Grass", "Normal", "Ground"),
        allowed_events=_events(),
        transitions=(
            SafariZone.MOUNTAIN_FOOTHILL,
            SafariZone.ROCKY_SLOPE,
            SafariZone.FROZEN_PASS,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.CAVE_ENTRANCE,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Rock", "Ground", "Dark"),
        allowed_events=_events(),
        transitions=(
            SafariZone.MOUNTAIN_FOOTHILL,
            SafariZone.DEEP_CAVE,
            SafariZone.ROCKY_SLOPE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.DEEP_CAVE,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Rock", "Dark", "Ghost", "Steel"),
        allowed_events=_events(SafariThematicEvent.DISTORTION),
        transitions=(
            SafariZone.CAVE_ENTRANCE,
            SafariZone.UNDERGROUND_LAKE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.HIGH_RIDGE,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Flying", "Dragon", "Rock"),
        allowed_events=_events(),
        transitions=(
            SafariZone.ROCKY_SLOPE,
            SafariZone.SUMMIT,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.FROZEN_PASS,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Ice", "Rock", "Steel"),
        allowed_events=_events(),
        transitions=(
            SafariZone.VALLEY,
            SafariZone.SUMMIT,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.UNDERGROUND_LAKE,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Water", "Rock", "Ground"),
        allowed_events=_events(SafariThematicEvent.FISHING),
        transitions=(SafariZone.DEEP_CAVE,),
    ),
    SafariZoneDefinition(
        zone=SafariZone.SUMMIT,
        safari_map=SafariMap.MOUNTAIN,
        base_type_weights=_type_weights("Flying", "Ice", "Dragon"),
        allowed_events=_events(),
        transitions=(
            SafariZone.HIGH_RIDGE,
            SafariZone.FROZEN_PASS,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.COAST_SHORE,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Water", "Flying", "Normal"),
        allowed_events=_events(SafariThematicEvent.MIGRATION),
        transitions=(
            SafariZone.ROCKY_BEACH,
            SafariZone.TIDAL_POOLS,
            SafariZone.COASTAL_PATH,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.ROCKY_BEACH,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Water", "Rock", "Fighting"),
        allowed_events=_events(),
        transitions=(
            SafariZone.COAST_SHORE,
            SafariZone.SEA_CAVE,
            SafariZone.CLIFFSIDE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.TIDAL_POOLS,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Water", "Poison", "Bug"),
        allowed_events=_events(SafariThematicEvent.FISHING),
        transitions=(
            SafariZone.COAST_SHORE,
            SafariZone.LAGOON,
            SafariZone.MANGROVE_EDGE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.COASTAL_PATH,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Flying", "Normal", "Electric"),
        allowed_events=_events(),
        transitions=(
            SafariZone.COAST_SHORE,
            SafariZone.CLIFFSIDE,
            SafariZone.DUNES,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.SEA_CAVE,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Water", "Rock", "Dark"),
        allowed_events=_events(SafariThematicEvent.DISTORTION),
        transitions=(
            SafariZone.ROCKY_BEACH,
            SafariZone.LAGOON,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.CLIFFSIDE,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Flying", "Rock", "Dragon"),
        allowed_events=_events(),
        transitions=(
            SafariZone.ROCKY_BEACH,
            SafariZone.COASTAL_PATH,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.LAGOON,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Water", "Grass", "Fairy"),
        allowed_events=_events(SafariThematicEvent.FISHING),
        transitions=(
            SafariZone.TIDAL_POOLS,
            SafariZone.SEA_CAVE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.MANGROVE_EDGE,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Water", "Grass", "Poison"),
        allowed_events=_events(),
        transitions=(
            SafariZone.TIDAL_POOLS,
            SafariZone.DUNES,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.DUNES,
        safari_map=SafariMap.COAST,
        base_type_weights=_type_weights("Ground", "Normal", "Flying"),
        allowed_events=_events(),
        transitions=(
            SafariZone.COASTAL_PATH,
            SafariZone.MANGROVE_EDGE,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.SWAMP_EDGE,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Water", "Poison", "Grass"),
        allowed_events=_events(),
        transitions=(
            SafariZone.MUDDY_TRAIL,
            SafariZone.SHALLOW_WATER,
            SafariZone.DENSE_REEDS,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.MUDDY_TRAIL,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Ground", "Poison", "Bug"),
        allowed_events=_events(),
        transitions=(
            SafariZone.SWAMP_EDGE,
            SafariZone.DEAD_FOREST,
            SafariZone.MISTY_CLEARING,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.SHALLOW_WATER,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Water", "Ground", "Poison"),
        allowed_events=_events(SafariThematicEvent.FISHING),
        transitions=(
            SafariZone.SWAMP_EDGE,
            SafariZone.DEEP_MARSH,
            SafariZone.DENSE_REEDS,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.DENSE_REEDS,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Grass", "Bug", "Flying"),
        allowed_events=_events(SafariThematicEvent.NEST),
        transitions=(
            SafariZone.SWAMP_EDGE,
            SafariZone.SHALLOW_WATER,
            SafariZone.NESTING_GROUND,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.DEAD_FOREST,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Ghost", "Dark", "Poison"),
        allowed_events=_events(),
        transitions=(
            SafariZone.MUDDY_TRAIL,
            SafariZone.MISTY_CLEARING,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.DEEP_MARSH,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Water", "Poison", "Dark"),
        allowed_events=_events(SafariThematicEvent.FISHING),
        transitions=(
            SafariZone.SHALLOW_WATER,
            SafariZone.NESTING_GROUND,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.MISTY_CLEARING,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Ghost", "Fairy", "Psychic"),
        allowed_events=_events(),
        transitions=(
            SafariZone.MUDDY_TRAIL,
            SafariZone.DEAD_FOREST,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.NESTING_GROUND,
        safari_map=SafariMap.SWAMP,
        base_type_weights=_type_weights("Bug", "Flying"),
        allowed_events=_events(SafariThematicEvent.NEST),
        transitions=(
            SafariZone.DENSE_REEDS,
            SafariZone.DEEP_MARSH,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.PLAINS_TRAIL,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Normal", "Ground", "Fighting"),
        allowed_events=_events(),
        transitions=(
            SafariZone.OPEN_FIELD,
            SafariZone.TALL_GRASS,
            SafariZone.LOW_HILLS,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.OPEN_FIELD,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Normal", "Flying", "Electric"),
        allowed_events=_events(SafariThematicEvent.MIGRATION),
        transitions=(
            SafariZone.PLAINS_TRAIL,
            SafariZone.FLOWER_MEADOW,
            SafariZone.WINDY_FIELD,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.TALL_GRASS,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Grass", "Bug", "Normal"),
        allowed_events=_events(),
        transitions=(
            SafariZone.PLAINS_TRAIL,
            SafariZone.RIVER_CROSSING,
            SafariZone.HERDING_GROUNDS,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.LOW_HILLS,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Ground", "Rock", "Fighting"),
        allowed_events=_events(),
        transitions=(
            SafariZone.PLAINS_TRAIL,
            SafariZone.WINDY_FIELD,
            SafariZone.ROCKY_OUTCROP,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.FLOWER_MEADOW,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Grass", "Fairy", "Bug"),
        allowed_events=_events(),
        transitions=(
            SafariZone.OPEN_FIELD,
            SafariZone.RIVER_CROSSING,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.WINDY_FIELD,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Flying", "Electric", "Normal"),
        allowed_events=_events(),
        transitions=(
            SafariZone.OPEN_FIELD,
            SafariZone.LOW_HILLS,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.RIVER_CROSSING,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Water", "Grass", "Flying"),
        allowed_events=_events(SafariThematicEvent.FISHING),
        transitions=(
            SafariZone.TALL_GRASS,
            SafariZone.FLOWER_MEADOW,
        ),
    ),
    SafariZoneDefinition(
        zone=SafariZone.HERDING_GROUNDS,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Normal", "Ground", "Fighting"),
        allowed_events=_events(SafariThematicEvent.MIGRATION),
        transitions=(SafariZone.TALL_GRASS,),
    ),
    SafariZoneDefinition(
        zone=SafariZone.ROCKY_OUTCROP,
        safari_map=SafariMap.PLAINS,
        base_type_weights=_type_weights("Rock", "Ground", "Steel"),
        allowed_events=_events(SafariThematicEvent.DEPOSIT),
        transitions=(SafariZone.LOW_HILLS,),
    ),
)


SAFARI_ZONE_DEFINITION_BY_ZONE: dict[SafariZone, SafariZoneDefinition] = {
    definition.zone: definition for definition in SAFARI_ZONE_DEFINITIONS
}


SAFARI_VALID_WEATHER_BY_MAP: dict[SafariMap, tuple[SafariWeather, ...]] = {
    SafariMap.FOREST: (
        SafariWeather.CLEAR,
        SafariWeather.RAIN,
        SafariWeather.FOG,
    ),
    SafariMap.MOUNTAIN: (
        SafariWeather.CLEAR,
        SafariWeather.FOG,
        SafariWeather.STORM,
        SafariWeather.SNOW,
    ),
    SafariMap.COAST: (
        SafariWeather.CLEAR,
        SafariWeather.RAIN,
        SafariWeather.FOG,
        SafariWeather.STORM,
    ),
    SafariMap.SWAMP: (
        SafariWeather.CLEAR,
        SafariWeather.RAIN,
        SafariWeather.FOG,
    ),
    SafariMap.PLAINS: (
        SafariWeather.CLEAR,
        SafariWeather.RAIN,
        SafariWeather.FOG,
        SafariWeather.STORM,
    ),
}


WEATHER_WEIGHTS: dict[SafariWeather, int] = {
    SafariWeather.CLEAR: 50,
    SafariWeather.RAIN: 20,
    SafariWeather.FOG: 15,
    SafariWeather.STORM: 10,
    SafariWeather.SNOW: 5,
}


TIME_OF_DAY_WEIGHTS: dict[SafariTimeOfDay, int] = {
    SafariTimeOfDay.DAY: 50,
    SafariTimeOfDay.SUNSET: 20,
    SafariTimeOfDay.NIGHT: 30,
}
