from __future__ import annotations

from dataclasses import dataclass

from core.creature.base_stats import BaseStats


@dataclass(frozen=True)
class Species:
    id: int
    name: str

    # Clasificación
    generation: int
    habitat: str | None
    is_baby: bool
    is_legendary: bool
    is_mythical: bool

    # Características
    types: list[str]
    base_stats: BaseStats
    height: int
    weight: int
    capture_rate: int

    # Capacidades
    forms_switchable: bool

    # Relaciones
    evolution_chain: EvolutionChain
    variants: list[Variant]