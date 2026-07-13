from dataclasses import dataclass

from core.safari.domain import SafariThematicEvent
from core.safari.encounter import SafariEncounter


@dataclass(frozen=True, slots=True)
class SafariGeneratedEncounter:
    encounter: SafariEncounter
    event: SafariThematicEvent

    def __post_init__(self) -> None:
        if not isinstance(self.encounter, SafariEncounter):
            raise ValueError("encounter must be a SafariEncounter.")
        if not isinstance(self.event, SafariThematicEvent):
            raise ValueError("event must be a SafariThematicEvent.")
