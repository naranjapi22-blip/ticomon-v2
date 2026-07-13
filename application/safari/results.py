from dataclasses import dataclass
from enum import Enum
from typing import Mapping

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
    SafariEncounterStatus,
    SafariRegistrationStatus,
    SafariSessionStatus,
)
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.participant import SafariParticipant
from core.safari.registration import SafariRegistration
from core.safari.route import SafariRouteOption, SafariRouteSegment
from core.safari.route_vote import SafariRouteVote, SafariRouteVoteResult
from core.safari.session import SafariSession
from core.safari.unlock import SafariUnlock


class SafariCaptureSelectionState(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"


@dataclass(frozen=True, slots=True)
class OpenSafariRegistrationResult:
    registration: SafariRegistration
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
