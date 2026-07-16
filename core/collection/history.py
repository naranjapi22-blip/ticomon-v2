from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CollectionEntrySource(StrEnum):
    STARTER = "starter"
    CAPTURE = "capture"
    SAFARI = "safari"
    SHOP = "shop"
    EVOLUTION = "evolution"
    TRADE = "trade"
    BACKFILL = "backfill"


@dataclass(frozen=True, slots=True)
class TrainerCollectionEntry:
    trainer_id: int
    species_id: int
    variant_id: int | None
    first_obtained_at: datetime
    source: CollectionEntrySource

    @property
    def identity(self) -> tuple[int, int | None]:
        return self.species_id, self.variant_id
