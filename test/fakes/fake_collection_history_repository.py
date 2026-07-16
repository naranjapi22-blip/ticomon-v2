from datetime import UTC, datetime

from core.collection.history import CollectionEntrySource, TrainerCollectionEntry
from core.collection.repository import CollectionHistoryRepository


class FakeCollectionHistoryRepository(CollectionHistoryRepository):
    def __init__(self) -> None:
        self.entries: dict[tuple[int, int, int | None], TrainerCollectionEntry] = {}
        self.claims: set[tuple[int, str, int]] = set()
        self.claim_calls: list[tuple[int, str, int, int]] = []

    async def record_creature(self, creature, source: CollectionEntrySource) -> bool:
        key = (
            creature.trainer_id,
            creature.species.id,
            creature.current_form.id if creature.current_form is not None else None,
        )
        if key in self.entries:
            return False
        self.entries[key] = TrainerCollectionEntry(
            trainer_id=creature.trainer_id,
            species_id=creature.species.id,
            variant_id=(
                creature.current_form.id if creature.current_form is not None else None
            ),
            first_obtained_at=datetime.now(UTC),
            source=source,
        )
        return True

    async def entries_for_trainer(self, trainer_id: int):
        return tuple(
            entry
            for (stored_trainer_id, _, _), entry in self.entries.items()
            if stored_trainer_id == trainer_id
        )

    async def claimed_milestones(self, trainer_id: int):
        return frozenset(
            (collection_id, milestone)
            for stored_trainer_id, collection_id, milestone in self.claims
            if stored_trainer_id == trainer_id
        )

    async def claim(
        self,
        trainer_id: int,
        collection_id: str,
        milestone: int,
        entry_identities,
        candies,
        mints: int,
    ) -> bool:
        key = trainer_id, collection_id, milestone
        self.claim_calls.append(
            (trainer_id, collection_id, milestone, len(entry_identities))
        )
        if key in self.claims:
            return False
        self.claims.add(key)
        return True

    async def backfill_existing_creatures(self) -> int:
        return 0
