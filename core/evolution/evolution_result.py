from __future__ import annotations

from dataclasses import dataclass

from core.candy.candy_bundle import CandyBundle
from core.evolution.evolution_failure_reason import EvolutionFailureReason
from core.species.species import Species


@dataclass(frozen=True, slots=True)
class EvolutionResult:
    """
    Represents the result of an evolution attempt.
    """

    success: bool

    previous_species: Species
    evolved_species: Species | None

    consumed_candies: CandyBundle

    failure_reason: EvolutionFailureReason | None = None

    @classmethod
    def succeeded(
        cls,
        previous_species: Species,
        evolved_species: Species,
        consumed_candies: CandyBundle,
    ) -> "EvolutionResult":
        return cls(
            success=True,
            previous_species=previous_species,
            evolved_species=evolved_species,
            consumed_candies=consumed_candies,
        )

    @classmethod
    def failed(
        cls,
        previous_species: Species,
        reason: EvolutionFailureReason,
    ) -> "EvolutionResult":
        return cls(
            success=False,
            previous_species=previous_species,
            evolved_species=None,
            consumed_candies=CandyBundle(),
            failure_reason=reason,
        )
