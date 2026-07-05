from __future__ import annotations

from dataclasses import dataclass

from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.species.species import Species
from core.species.variant import Variant


@dataclass
class Opportunity:
    """
    Representa una oportunidad temporal de interacción dentro del mundo.

    Una Opportunity ya conoce todas las características individuales de la
    futura Creature, pero todavía no pertenece a ningún Trainer.
    """

    id: int

    # Identidad
    species: Species
    variant: Variant | None

    # Características individuales
    ivs: IVs
    size: float
    nature: Nature
    is_shiny: bool

    # Estado inicial
    initial_form: str | None

    # Interacción permitida
    interaction: str