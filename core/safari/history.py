from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from core.creature.creature import Creature
from core.safari.capture_resolution import SafariEncounterResolution
from core.safari.domain import SafariPhase
from core.safari.encounter import SafariEncounter
from core.safari.route import SafariRouteSegment
from core.safari.route_vote import SafariRouteVoteResult


@dataclass(frozen=True, slots=True)
class SafariRouteProgressEntry:
    vote_result: SafariRouteVoteResult
    destination_segment: SafariRouteSegment
    phase: SafariPhase


@dataclass(frozen=True, slots=True)
class SafariCapturedCreatureSnapshot:
    slot_id: UUID
    trainer_id: int
    creature_id: int
    creature: Creature


@dataclass(frozen=True, slots=True)
class SafariEncounterHistoryEntry:
    encounter: SafariEncounter
    resolution: SafariEncounterResolution
    captured_creatures: tuple[SafariCapturedCreatureSnapshot, ...]
    eligible_participant_ids: frozenset[int]
