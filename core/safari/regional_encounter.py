from dataclasses import dataclass

from core.safari.domain import (
    SafariComposition,
    SafariRegionalEncounterForm,
    SafariThematicEvent,
)
from core.safari.encounter import SafariEncounter


@dataclass(frozen=True, slots=True)
class SafariGeneratedRegionalEncounter:
    encounter: SafariEncounter
    event: SafariThematicEvent
    regional_form: SafariRegionalEncounterForm

    def __post_init__(self) -> None:
        if not isinstance(self.encounter, SafariEncounter):
            raise ValueError("encounter must be a SafariEncounter.")
        if self.encounter.composition != SafariComposition.REGIONAL:
            raise ValueError("regional encounter must use REGIONAL composition.")
        if not isinstance(self.event, SafariThematicEvent):
            raise ValueError("event must be a SafariThematicEvent.")
        if not isinstance(self.regional_form, SafariRegionalEncounterForm):
            raise ValueError("regional_form must be a SafariRegionalEncounterForm.")
