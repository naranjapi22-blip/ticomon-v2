from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from core.safari.domain import SafariThematicEvent, SafariZone


def _freeze_type_weights(
    type_weights: Mapping[str, float],
) -> Mapping[str, float]:
    copied = dict(type_weights)

    for type_name, weight in copied.items():
        if not type_name or type_name != type_name.strip().lower():
            raise ValueError("type weight keys must use canonical lowercase names.")
        if weight <= 0:
            raise ValueError("type weights must be positive.")

    return MappingProxyType(copied)


def _freeze_events(
    allowed_events: tuple[SafariThematicEvent, ...],
) -> tuple[SafariThematicEvent, ...]:
    copied = tuple(allowed_events)
    if SafariThematicEvent.NONE not in copied:
        raise ValueError("allowed_events must include NONE.")
    return copied


@dataclass(frozen=True, slots=True)
class SafariRouteOption:
    id: str
    source_zone: SafariZone
    destination_zone: SafariZone
    type_weight_modifiers: Mapping[str, float]
    allowed_events: tuple[SafariThematicEvent, ...]
    narrative_key: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("id is required.")
        if not isinstance(self.source_zone, SafariZone):
            raise ValueError("source_zone must be a SafariZone.")
        if not isinstance(self.destination_zone, SafariZone):
            raise ValueError("destination_zone must be a SafariZone.")
        if not self.narrative_key.strip():
            raise ValueError("narrative_key is required.")

        object.__setattr__(
            self,
            "type_weight_modifiers",
            _freeze_type_weights(self.type_weight_modifiers),
        )
        object.__setattr__(
            self,
            "allowed_events",
            _freeze_events(self.allowed_events),
        )

    @property
    def stays_in_same_zone(self) -> bool:
        return self.source_zone == self.destination_zone


@dataclass(slots=True)
class SafariRouteSegment:
    zone: SafariZone
    remaining_encounters: int
    type_weight_modifiers: Mapping[str, float]
    allowed_events: tuple[SafariThematicEvent, ...]
    source_option_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.zone, SafariZone):
            raise ValueError("zone must be a SafariZone.")
        if self.remaining_encounters <= 0:
            raise ValueError("remaining_encounters must be positive.")
        if self.source_option_id is not None and not self.source_option_id.strip():
            raise ValueError("source_option_id cannot be empty.")

        self.type_weight_modifiers = _freeze_type_weights(self.type_weight_modifiers)
        self.allowed_events = _freeze_events(self.allowed_events)

    @property
    def is_complete(self) -> bool:
        return self.remaining_encounters == 0

    def complete_encounter(self) -> None:
        if self.is_complete:
            raise ValueError("route segment is already complete.")

        self.remaining_encounters -= 1
