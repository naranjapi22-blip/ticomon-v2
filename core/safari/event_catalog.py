from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from core.safari.domain import (
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariComposition,
    SafariPhase,
    SafariThematicEvent,
    SafariZone,
)
from core.safari.encounter_context import SafariEncounterContext

COMMON_SAFARI_COMPOSITIONS = frozenset(
    {
        SafariComposition.NORMAL,
        SafariComposition.DUEL,
        SafariComposition.HERD,
        SafariComposition.SOLITARY,
        SafariComposition.BABY_NEST,
    }
)

EXTRAORDINARY_SAFARI_COMPOSITIONS = frozenset(
    {SafariComposition.LEGENDARY, SafariComposition.MYTHICAL}
)


EVENT_WEIGHTS: Mapping[SafariThematicEvent, float] = MappingProxyType(
    {
        SafariThematicEvent.NONE: 50.0,
        SafariThematicEvent.VOLCANIC_ACTIVITY: 6.0,
        SafariThematicEvent.FISHING: 10.0,
        SafariThematicEvent.MIGRATION: 8.0,
        SafariThematicEvent.DISTORTION: 5.0,
        SafariThematicEvent.DEPOSIT: 7.0,
        SafariThematicEvent.GRAVEYARD: 6.0,
        SafariThematicEvent.ANCIENT_RUINS: 6.0,
        SafariThematicEvent.RAINBOW: 5.0,
        SafariThematicEvent.DEN: 7.0,
        SafariThematicEvent.NEST: 8.0,
    }
)


EVENT_COMPOSITION_COMPATIBILITY: Mapping[
    SafariThematicEvent,
    frozenset[SafariComposition],
] = MappingProxyType(
    {
        SafariThematicEvent.NONE: (
            COMMON_SAFARI_COMPOSITIONS | EXTRAORDINARY_SAFARI_COMPOSITIONS
        ),
        SafariThematicEvent.VOLCANIC_ACTIVITY: frozenset(
            {
                SafariComposition.NORMAL,
                SafariComposition.DUEL,
                SafariComposition.HERD,
                SafariComposition.SOLITARY,
                SafariComposition.LEGENDARY,
                SafariComposition.MYTHICAL,
            }
        ),
        SafariThematicEvent.FISHING: frozenset(
            {
                SafariComposition.NORMAL,
                SafariComposition.DUEL,
                SafariComposition.HERD,
                SafariComposition.SOLITARY,
                SafariComposition.LEGENDARY,
                SafariComposition.MYTHICAL,
            }
        ),
        SafariThematicEvent.MIGRATION: frozenset(
            {
                SafariComposition.NORMAL,
                SafariComposition.DUEL,
                SafariComposition.HERD,
            }
        ),
        SafariThematicEvent.DISTORTION: frozenset(
            {
                SafariComposition.NORMAL,
                SafariComposition.DUEL,
                SafariComposition.SOLITARY,
            }
        ),
        SafariThematicEvent.DEPOSIT: frozenset(
            {
                SafariComposition.NORMAL,
                SafariComposition.DUEL,
                SafariComposition.HERD,
                SafariComposition.SOLITARY,
            }
        ),
        SafariThematicEvent.GRAVEYARD: frozenset(
            {
                SafariComposition.NORMAL,
                SafariComposition.DUEL,
                SafariComposition.HERD,
                SafariComposition.SOLITARY,
            }
        ),
        SafariThematicEvent.ANCIENT_RUINS: frozenset(
            {
                SafariComposition.NORMAL,
                SafariComposition.DUEL,
                SafariComposition.SOLITARY,
            }
        ),
        SafariThematicEvent.RAINBOW: COMMON_SAFARI_COMPOSITIONS,
        SafariThematicEvent.DEN: frozenset(
            {
                SafariComposition.DUEL,
                SafariComposition.HERD,
                SafariComposition.SOLITARY,
            }
        ),
        SafariThematicEvent.NEST: frozenset({SafariComposition.BABY_NEST}),
    }
)


def _freeze_type_modifiers(
    modifiers_by_event: Mapping[SafariThematicEvent, Mapping[str, float]],
) -> Mapping[SafariThematicEvent, Mapping[str, float]]:
    frozen: dict[SafariThematicEvent, Mapping[str, float]] = {}
    for event, modifiers in modifiers_by_event.items():
        copied = dict(modifiers)
        for type_name, modifier in copied.items():
            if not type_name or type_name != type_name.strip().lower():
                raise ValueError(
                    "event type modifier keys must be canonical lowercase."
                )
            if modifier < 0:
                raise ValueError("event type modifiers cannot be negative.")
        frozen[event] = MappingProxyType(copied)
    return MappingProxyType(frozen)


EVENT_TYPE_MODIFIERS = _freeze_type_modifiers(
    {
        SafariThematicEvent.NONE: {},
        SafariThematicEvent.VOLCANIC_ACTIVITY: {"fire": 1.7, "rock": 1.3},
        SafariThematicEvent.FISHING: {"water": 1.8},
        SafariThematicEvent.MIGRATION: {"flying": 1.4, "normal": 1.3},
        SafariThematicEvent.DISTORTION: {"psychic": 1.5, "ghost": 1.5},
        SafariThematicEvent.DEPOSIT: {
            "rock": 1.5,
            "ground": 1.4,
            "steel": 1.4,
        },
        SafariThematicEvent.GRAVEYARD: {"ghost": 1.8, "dark": 1.2},
        SafariThematicEvent.ANCIENT_RUINS: {
            "rock": 1.3,
            "psychic": 1.3,
            "ghost": 1.3,
        },
        SafariThematicEvent.RAINBOW: {"fairy": 1.5, "flying": 1.2},
        SafariThematicEvent.DEN: {
            "dragon": 1.3,
            "dark": 1.3,
            "fighting": 1.2,
        },
        SafariThematicEvent.NEST: {
            "bug": 1.3,
            "flying": 1.2,
            "grass": 1.2,
        },
    }
)


EVENT_REQUIRED_TYPES: Mapping[SafariThematicEvent, frozenset[str]] = MappingProxyType(
    {
        event: (
            frozenset({"water"})
            if event == SafariThematicEvent.FISHING
            else frozenset()
        )
        for event in SafariThematicEvent
    }
)


EVENTS_BY_PHASE: Mapping[SafariPhase, frozenset[SafariThematicEvent]] = (
    MappingProxyType(
        {
            SafariPhase.START: frozenset(
                {
                    SafariThematicEvent.NONE,
                    SafariThematicEvent.FISHING,
                    SafariThematicEvent.MIGRATION,
                    SafariThematicEvent.DEPOSIT,
                    SafariThematicEvent.NEST,
                }
            ),
            SafariPhase.DEVELOPMENT: frozenset(SafariThematicEvent),
            SafariPhase.FINAL: frozenset(SafariThematicEvent),
        }
    )
)


EVENTS_BY_ZONE: Mapping[SafariZone, frozenset[SafariThematicEvent]] = MappingProxyType(
    {
        zone: frozenset(definition.allowed_events)
        for zone, definition in SAFARI_ZONE_DEFINITION_BY_ZONE.items()
    }
)


def available_events_for(
    context: SafariEncounterContext,
    composition: SafariComposition,
) -> frozenset[SafariThematicEvent]:
    if composition not in COMMON_SAFARI_COMPOSITIONS:
        raise ValueError("event availability requires a common Safari composition.")
    available = (
        EVENTS_BY_ZONE[context.zone]
        & context.route_allowed_events
        & EVENTS_BY_PHASE[context.phase]
    )
    compatible = frozenset(
        event
        for event in available
        if composition in EVENT_COMPOSITION_COMPATIBILITY[event]
    )
    return compatible or frozenset({SafariThematicEvent.NONE})


def available_regional_events_for(
    context: SafariEncounterContext,
) -> frozenset[SafariThematicEvent]:
    available = (
        EVENTS_BY_ZONE[context.zone]
        & context.route_allowed_events
        & EVENTS_BY_PHASE[context.phase]
    )
    return available or frozenset({SafariThematicEvent.NONE})


def available_extraordinary_events_for(
    context: SafariEncounterContext,
    composition: SafariComposition,
) -> frozenset[SafariThematicEvent]:
    if composition not in EXTRAORDINARY_SAFARI_COMPOSITIONS:
        raise ValueError(
            "event availability requires an extraordinary Safari composition."
        )
    available = (
        EVENTS_BY_ZONE[context.zone]
        & context.route_allowed_events
        & EVENTS_BY_PHASE[context.phase]
    )
    compatible = frozenset(
        event
        for event in available
        if composition in EVENT_COMPOSITION_COMPATIBILITY[event]
    )
    return compatible or frozenset({SafariThematicEvent.NONE})
