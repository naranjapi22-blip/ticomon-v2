from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping
from uuid import UUID

from core.candy.candy_bundle import CandyBundle
from core.creature.creature import Creature
from core.safari.capture import (
    SafariCaptureSelection,
    SafariPersistedCapture,
    SafariPersistedEncounterResult,
)
from core.safari.capture_resolution import (
    SafariEncounterResolution,
    SafariSlotOutcome,
)
from core.safari.domain import (
    SafariComposition,
    SafariEncounterStatus,
    SafariFinishReason,
    SafariMap,
    SafariPhase,
    SafariRegistrationStatus,
    SafariSessionStatus,
    SafariSlotStatus,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.participant import SafariParticipant
from core.safari.registration import SafariRegistration
from core.safari.route import SafariRouteOption, SafariRouteSegment
from core.safari.route_vote import SafariRouteVote, SafariRouteVoteResult
from core.safari.session import SafariSession
from core.safari.unlock import SafariUnlock
from core.species.species import Species
from core.species.variant import Variant


class SafariCaptureSelectionState(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"


@dataclass(frozen=True, slots=True)
class OpenSafariRegistrationResult:
    registration: SafariRegistration
    unlock: SafariUnlock
    level: int
    encounter_count: int
    balls_per_participant: int
    capacity: int


@dataclass(frozen=True, slots=True)
class JoinSafariRegistrationResult:
    added: bool
    participant_count: int
    capacity: int
    status: SafariRegistrationStatus


@dataclass(frozen=True, slots=True)
class CancelSafariRegistrationResult:
    registration: SafariRegistration


@dataclass(frozen=True, slots=True)
class StartSafariResult:
    session: SafariSession
    unlock: SafariUnlock
    generated_encounter: SafariGeneratedEncounter


@dataclass(frozen=True, slots=True)
class OpenSafariRouteVoteResult:
    session: SafariSession
    vote: SafariRouteVote
    options: tuple[SafariRouteOption, ...]


@dataclass(frozen=True, slots=True)
class CastSafariRouteVoteResult:
    session: SafariSession
    vote: SafariRouteVote
    trainer_id: int
    option_id: str
    replaced: bool


@dataclass(frozen=True, slots=True)
class ResolveSafariRouteVoteResult:
    session: SafariSession
    vote_result: SafariRouteVoteResult
    selected_option: SafariRouteOption
    destination_segment: SafariRouteSegment
    next_encounter: SafariGeneratedEncounter


@dataclass(frozen=True, slots=True)
class SafariCapturedCreatureSummary:
    slot_id: UUID
    trainer_id: int
    creature_id: int
    species: Species
    collection_number: int
    is_shiny: bool
    current_form: Variant | None


@dataclass(frozen=True, slots=True)
class SafariEncounterSlotSummary:
    slot_id: UUID
    species: Species
    status: SafariSlotStatus
    winner_trainer_id: int | None
    attempts_executed: int
    balls_committed: int
    captured_creature: SafariCapturedCreatureSummary | None


@dataclass(frozen=True, slots=True)
class SafariEncounterSummary:
    encounter_id: UUID
    composition: SafariComposition
    is_regional_herd: bool
    slot_summaries: tuple[SafariEncounterSlotSummary, ...]
    captured_slot_count: int
    escaped_slot_count: int
    attempts_executed: int
    balls_committed: int


@dataclass(frozen=True, slots=True)
class SafariRouteSegmentSummary:
    zone: SafariZone
    phase: SafariPhase
    remaining_encounters: int
    source_option_id: str | None
    vote_result: SafariRouteVoteResult | None = None


@dataclass(frozen=True, slots=True)
class SafariRouteSummary:
    safari_map: SafariMap
    weather: SafariWeather
    time_of_day: SafariTimeOfDay
    segments: tuple[SafariRouteSegmentSummary, ...]


@dataclass(frozen=True, slots=True)
class SafariParticipantSummary:
    rank: int
    trainer_id: int
    capture_count: int
    shiny_capture_count: int
    captured_creatures: tuple[SafariCapturedCreatureSummary, ...]
    initial_balls: int
    balls_used: int
    balls_remaining: int
    attempts_executed: int
    slots_won: int
    encounters_participated: int


@dataclass(frozen=True, slots=True)
class SafariTotalsSummary:
    encounters_completed: int
    pokemon_seen: int
    slots_captured: int
    slots_escaped: int
    attempts_executed: int
    balls_committed: int


@dataclass(frozen=True, slots=True)
class SafariExtraordinarySummary:
    legendary_seen: bool
    mythical_seen: bool
    shiny_encounter_seen: bool
    regional_herd_seen: bool


@dataclass(frozen=True, slots=True)
class SafariFinalSummary:
    guild_id: int
    session_id: UUID
    level: int
    safari_map: SafariMap
    weather: SafariWeather
    time_of_day: SafariTimeOfDay
    started_at: datetime
    finished_at: datetime
    finish_reason: SafariFinishReason
    ranking: tuple[SafariParticipantSummary, ...]
    route: SafariRouteSummary
    encounters: tuple[SafariEncounterSummary, ...]
    totals: SafariTotalsSummary
    extraordinary: SafariExtraordinarySummary


@dataclass(frozen=True, slots=True)
class FinishSafariResult:
    session: SafariSession
    summary: SafariFinalSummary


@dataclass(frozen=True, slots=True)
class SelectSafariCaptureResult:
    session: SafariSession
    encounter: SafariEncounter
    participant: SafariParticipant
    slot: SafariEncounterSlot
    balls_selected: int
    balls_available: int
    selection: SafariCaptureSelection | None
    state: SafariCaptureSelectionState


@dataclass(frozen=True, slots=True)
class DeclineSafariCaptureResult:
    session: SafariSession
    encounter: SafariEncounter
    participant: SafariParticipant
    selection: SafariCaptureSelection | None
    balls_available: int
    state: SafariCaptureSelectionState


@dataclass(frozen=True, slots=True)
class ConfirmSafariCaptureSelectionResult:
    session: SafariSession
    encounter: SafariEncounter
    participant: SafariParticipant
    selection: SafariCaptureSelection
    balls_spent: int
    balls_available: int
    state: SafariCaptureSelectionState


@dataclass(frozen=True, slots=True)
class CloseSafariCaptureSelectionResult:
    session: SafariSession
    encounter: SafariEncounter
    confirmed_participant_ids: tuple[int, ...]
    declined_participant_ids: tuple[int, ...]
    state: SafariEncounterStatus


@dataclass(frozen=True, slots=True)
class SafariCaptureSlotApplicationResult:
    slot_outcome: SafariSlotOutcome
    creature: Creature | None
    persisted_capture: SafariPersistedCapture | None
    reward: CandyBundle
    collection_number: int | None


@dataclass(frozen=True, slots=True)
class ResolveSafariCaptureResult:
    session: SafariSession
    encounter_resolution: SafariEncounterResolution
    persisted_result: SafariPersistedEncounterResult
    slot_results: tuple[SafariCaptureSlotApplicationResult, ...]
    rewards_by_trainer: Mapping[int, CandyBundle]
    balls_committed_by_trainer: Mapping[int, int]
    next_session_status: SafariSessionStatus
