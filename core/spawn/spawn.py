from __future__ import annotations

from dataclasses import dataclass

from core.opportunity.opportunity import Opportunity


@dataclass
class Spawn:
    """
    Representa un Spawn ocurrido en el mundo.

    Un Spawn agrupa las Opportunities generadas durante ese evento.
    """

    id: int
    opportunities: list[Opportunity]

    @classmethod
    def create(cls, id: int, opportunities: list[Opportunity]) -> "Spawn":
        return cls(
            id=id,
            opportunities=opportunities,
        )