from abc import ABC, abstractmethod

from core.candy.candy_bundle import CandyBundle
from core.creature.creature import Creature

from .history import CollectionEntrySource, TrainerCollectionEntry


class CollectionHistoryRepository(ABC):
    @abstractmethod
    async def record_creature(
        self,
        creature: Creature,
        source: CollectionEntrySource,
    ) -> bool:
        """Records the trainer's first canonical acquisition of a creature."""

    @abstractmethod
    async def entries_for_trainer(
        self,
        trainer_id: int,
    ) -> tuple[TrainerCollectionEntry, ...]:
        """Returns immutable collection history for one trainer."""

    @abstractmethod
    async def claimed_milestones(
        self,
        trainer_id: int,
    ) -> frozenset[tuple[str, int]]:
        """Returns the collection milestone keys already claimed by a trainer."""

    @abstractmethod
    async def claim(
        self,
        trainer_id: int,
        collection_id: str,
        milestone: int,
        entry_identities: tuple[tuple[int, int | None], ...],
        candies: CandyBundle,
        mints: int,
    ) -> bool:
        """Atomically records one claim and grants its rewards once."""

    @abstractmethod
    async def backfill_existing_creatures(self) -> int:
        """Idempotently records collection entries for currently owned creatures."""
