from __future__ import annotations

from dataclasses import dataclass

from core.opportunity.opportunity import Opportunity


@dataclass
class Spawn:
    """Represents a Spawn that occurred in the world."""

    opportunities: list[Opportunity]

    @classmethod
    def create(
        cls,
        opportunities: list[Opportunity],
    ) -> "Spawn":
        return cls(
            opportunities=opportunities,
        )
