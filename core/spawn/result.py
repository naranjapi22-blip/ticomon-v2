from dataclasses import dataclass

from core.opportunity.opportunity import Opportunity


@dataclass(frozen=True, slots=True)
class SpawnResult:
    """
    Result produced by the Spawn Engine.
    """

    opportunities: tuple[Opportunity, ...]
