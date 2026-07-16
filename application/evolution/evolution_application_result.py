from dataclasses import dataclass

from core.candy.candy_bundle import CandyBundle
from core.creature.creature import Creature
from core.evolution.evolution_failure_reason import EvolutionFailureReason
from core.species.species import Species


@dataclass(frozen=True)
class EvolutionApplicationResult:
    """
    Result returned by the Evolution application service.
    """

    success: bool

    creature: Creature

    previous_species: Species

    evolved_species: Species | None

    consumed_candies: CandyBundle

    failure_reason: EvolutionFailureReason | None
    achievements: tuple = ()
