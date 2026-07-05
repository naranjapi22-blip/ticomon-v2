from __future__ import annotations

from dataclasses import dataclass

from core.species.species import Species

from core.creature.ivs import IVs


@dataclass
class Creature:
    """
    Representa un individuo único de una Species.

    Hereda las características comunes de su Species, pero posee su propio
    estado y características individuales.
    """

    id: int

    # Relación
    species: Species
    trainer_id: int | None

    # Características individuales
    ivs: IVs
    size: float
    nature: Nature

    # Estado
    current_form: str | None