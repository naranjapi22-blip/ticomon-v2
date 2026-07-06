from __future__ import annotations

from dataclasses import dataclass

from core.opportunity.opportunity import Opportunity


@dataclass
class Spawn:
    """
    Representa un Spawn ocurrido en el mundo.
    """

    opportunities: list[Opportunity]

    @classmethod
    def create(
        cls,
        opportunities: list[Opportunity],
    ) -> "Spawn":
        return cls(
            opportunities=opportunities,
        )
