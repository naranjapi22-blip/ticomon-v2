from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from core.safari.domain import (
    SAFARI_VALID_WEATHER_BY_MAP,
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariExtraordinaryFlags,
    SafariMap,
    SafariPhase,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)


def _freeze_type_modifiers(
    modifiers: Mapping[str, float],
) -> Mapping[str, float]:
    copied = dict(modifiers)
    for type_name, modifier in copied.items():
        if not type_name or type_name != type_name.strip().lower():
            raise ValueError("type modifier keys must use canonical lowercase names.")
        if modifier < 0:
            raise ValueError("type modifiers cannot be negative.")
    return MappingProxyType(copied)


@dataclass(frozen=True, slots=True)
class SafariEncounterContext:
    safari_map: SafariMap
    zone: SafariZone
    weather: SafariWeather
    time_of_day: SafariTimeOfDay
    phase: SafariPhase
    map_type_weight_modifiers: Mapping[str, float]
    zone_type_weight_modifiers: Mapping[str, float]
    route_type_weight_modifiers: Mapping[str, float]
    seen_species_ids: frozenset[int]
    route_allowed_events: frozenset[SafariThematicEvent] | None = None
    extraordinary_flags: SafariExtraordinaryFlags = field(
        default_factory=SafariExtraordinaryFlags
    )
    event_quota: int = 0
    generated_event_count: int = 0
    encounters_remaining: int = 0
    generated_event_types: frozenset[SafariThematicEvent] = field(
        default_factory=frozenset
    )

    def __post_init__(self) -> None:
        if not isinstance(self.safari_map, SafariMap):
            raise ValueError("safari_map must be a SafariMap.")
        if not isinstance(self.zone, SafariZone):
            raise ValueError("zone must be a SafariZone.")
        if SAFARI_ZONE_DEFINITION_BY_ZONE[self.zone].safari_map != self.safari_map:
            raise ValueError("zone must belong to safari_map.")
        if not isinstance(self.weather, SafariWeather):
            raise ValueError("weather must be a SafariWeather.")
        if self.weather not in SAFARI_VALID_WEATHER_BY_MAP[self.safari_map]:
            raise ValueError("weather is not valid for safari_map.")
        if not isinstance(self.time_of_day, SafariTimeOfDay):
            raise ValueError("time_of_day must be a SafariTimeOfDay.")
        if not isinstance(self.phase, SafariPhase):
            raise ValueError("phase must be a SafariPhase.")
        if not isinstance(self.extraordinary_flags, SafariExtraordinaryFlags):
            raise ValueError("extraordinary_flags must be SafariExtraordinaryFlags.")
        if self.event_quota < 0:
            raise ValueError("event_quota cannot be negative.")
        if self.generated_event_count < 0:
            raise ValueError("generated_event_count cannot be negative.")
        if self.encounters_remaining < 0:
            raise ValueError("encounters_remaining cannot be negative.")

        seen_species_ids = frozenset(self.seen_species_ids)
        if any(species_id <= 0 for species_id in seen_species_ids):
            raise ValueError("seen species IDs must be positive.")

        route_allowed_events = self.route_allowed_events
        if route_allowed_events is None:
            route_allowed_events = frozenset(
                SAFARI_ZONE_DEFINITION_BY_ZONE[self.zone].allowed_events
            )
        else:
            route_allowed_events = frozenset(route_allowed_events)
            if any(
                not isinstance(event, SafariThematicEvent)
                for event in route_allowed_events
            ):
                raise ValueError("route events must be SafariThematicEvent values.")
            if SafariThematicEvent.NONE not in route_allowed_events:
                raise ValueError("route events must include NONE.")

        object.__setattr__(
            self,
            "map_type_weight_modifiers",
            _freeze_type_modifiers(self.map_type_weight_modifiers),
        )
        object.__setattr__(
            self,
            "zone_type_weight_modifiers",
            _freeze_type_modifiers(self.zone_type_weight_modifiers),
        )
        object.__setattr__(
            self,
            "route_type_weight_modifiers",
            _freeze_type_modifiers(self.route_type_weight_modifiers),
        )
        object.__setattr__(self, "seen_species_ids", seen_species_ids)
        object.__setattr__(self, "route_allowed_events", route_allowed_events)
        generated_event_types = frozenset(self.generated_event_types)
        if any(
            not isinstance(event, SafariThematicEvent)
            or event is SafariThematicEvent.NONE
            for event in generated_event_types
        ):
            raise ValueError(
                "generated event types must be non-NONE SafariThematicEvent values."
            )
        object.__setattr__(self, "generated_event_types", generated_event_types)
