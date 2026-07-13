from dataclasses import dataclass

from core.safari.domain import SafariRegistrationStatus
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.registration import SafariRegistration
from core.safari.route import SafariRouteOption, SafariRouteSegment
from core.safari.route_vote import SafariRouteVote, SafariRouteVoteResult
from core.safari.session import SafariSession
from core.safari.unlock import SafariUnlock


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
