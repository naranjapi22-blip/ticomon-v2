from dataclasses import dataclass

from core.evolution.evolution_result import EvolutionResult


@dataclass(frozen=True, slots=True)
class EvolutionApplicationResult:
    """
    Result returned by the evolution application service.
    """

    evolution: EvolutionResult
