from dataclasses import dataclass

from core.safari.domain import SafariRegistrationStatus
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.registration import SafariRegistration
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
