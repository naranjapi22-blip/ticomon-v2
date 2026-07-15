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


EVENT_REQUIRED_TYPES: Mapping[SafariThematicEvent, frozenset[str]] = MappingProxyType(
    {
        SafariThematicEvent.NONE: frozenset(),
        SafariThematicEvent.VOLCANIC_ACTIVITY: frozenset({"fire", "rock"}),
        SafariThematicEvent.FISHING: frozenset({"water"}),
        SafariThematicEvent.MIGRATION: frozenset({"flying", "normal"}),
        SafariThematicEvent.DISTORTION: frozenset({"psychic", "ghost"}),
        SafariThematicEvent.DEPOSIT: frozenset({"rock", "ground", "steel"}),
        SafariThematicEvent.GRAVEYARD: frozenset({"ghost", "dark"}),
        SafariThematicEvent.ANCIENT_RUINS: frozenset({"rock", "psychic", "ghost"}),
        SafariThematicEvent.RAINBOW: frozenset({"fairy", "flying"}),
        SafariThematicEvent.DEN: frozenset({"dragon", "dark", "fighting"}),
        SafariThematicEvent.NEST: frozenset({"bug", "flying", "grass"}),
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
