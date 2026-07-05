from __future__ import annotations

from dataclasses import dataclass
from core.creature.base_stats import BaseStats
from core.evolution.evolution_chain import EvolutionChain
from core.species.variant import Variant


@dataclass(frozen=True)
class Species:
    # identidad interna del juego
    id: int
    name: str

    # gameplay core
    types: list[str]
    base_stats: BaseStats
    height: int
    weight: int
    capture_rate: int

    # sistemas de juego (opcionales)
    evolution_chain: EvolutionChain | None = None
    variants: list[Variant] | None = None