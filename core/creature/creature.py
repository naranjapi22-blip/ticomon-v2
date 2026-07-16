from __future__ import annotations

from dataclasses import dataclass

from core.creature.iv_rating import IVRating
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.creature.stat import Stat
from core.species.species import Species
from core.species.variant import Variant


@dataclass
class Creature:
    """
    Represents a unique individual of a Species.

    Inherits the common characteristics of its Species while having its own
    state and individual characteristics.
    """

    species: Species
    trainer_id: int | None

    ivs: IVs
    size: Size
    nature: Nature
    is_shiny: bool

    current_form: Variant | None
    minted_nature: Nature | None = None

    id: int | None = None
    collection_number: int | None = None
    original_trainer_id: int | None = None

    def __post_init__(self) -> None:
        if self.original_trainer_id is None and self.trainer_id is not None:
            self.original_trainer_id = self.trainer_id

    def stat_for(self, stat: Stat) -> int:
        return self.species.base_stats.for_stat(stat)

    def iv_for(self, stat: Stat) -> int:
        return self.ivs.for_stat(stat)

    def nature_modifier_for(self, stat: Stat) -> float:
        return self.effective_nature.modifier_for(stat)

    @property
    def effective_nature(self) -> Nature:
        return self.minted_nature or self.nature

    @property
    def iv_percentage(self) -> int:
        return IVRating.percentage(
            self.ivs,
        )
