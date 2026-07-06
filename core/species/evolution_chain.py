from __future__ import annotations

from dataclasses import dataclass

from .species import Species


@dataclass
class EvolutionChain:
    """
    Define las posibles evoluciones entre Species.

    Conoce únicamente las Species que participan en la cadena y la cantidad
    de caramelos necesaria para cada transición.
    """

    id: int
    species: list[Species]
    candy_requirements: dict[tuple[int, int], int]
