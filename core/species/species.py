from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Species:
    """
    Representa un tipo de criatura dentro del mundo de TicoMon.

    Una Species define las características comunes que comparten todas las
    Creature de esa especie. No conoce jugadores ni criaturas individuales.
    """

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
    base_stats: dict[str, int]
    height: int
    weight: int
    capture_rate: int

    # Capacidades
    forms_switchable: bool

    # Relaciones
    evolution_chain: "EvolutionChain"
    variants: list["Variant"]