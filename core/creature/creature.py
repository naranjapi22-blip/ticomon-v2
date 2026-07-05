from __future__ import annotations

from dataclasses import dataclass

from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.stat import Stat
from core.species.species import Species
from core.creature.size import Size

@dataclass
class Creature:
    """
    Representa un individuo único de una Species.

    Hereda las características comunes de su Species, pero posee su propio
    estado y características individuales.
    """

    # Identidad
    id: int

    # Relación
    species: Species
    trainer_id: int | None

    # Características individuales
    ivs: IVs
    size: Size
    nature: Nature
    is_shiny: bool

    # Estado
    current_form: str | None

    def stat_for(self, stat: Stat) -> int:
        return self.species.base_stats.for_stat(stat)

    def iv_for(self, stat: Stat) -> int:
        return self.ivs.for_stat(stat)

    def nature_modifier_for(self, stat: Stat) -> float:
        return self.nature.modifier_for(stat)