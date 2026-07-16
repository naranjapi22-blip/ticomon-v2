from datetime import UTC, datetime

from application.achievement.contracts import (
    AchievementActivityRepository,
    AchievementProgress,
    AchievementUnlock,
    AchievementUnlockRepository,
)
from core.achievement.activity import AchievementActivity, AchievementActivityType
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory


class FakeAchievementActivityRepository(AchievementActivityRepository):
    def __init__(self) -> None:
        self.activities: list[AchievementActivity] = []
        self._keys: set[tuple[int, AchievementActivityType, str]] = set()
        self._discovered_species: set[tuple[int, int]] = set()

    async def record(self, activity: AchievementActivity) -> bool:
        key = (activity.trainer_id, activity.activity_type, activity.idempotency_key)
        if key in self._keys:
            return False
        if activity.activity_type is AchievementActivityType.SPECIES_DISCOVERED:
            assert activity.species_id is not None
            discovered_key = (activity.trainer_id, activity.species_id)
            if discovered_key in self._discovered_species:
                return False
            self._discovered_species.add(discovered_key)
        self._keys.add(key)
        self.activities.append(activity)
        return True

    async def get_progress(self, trainer_id: int) -> AchievementProgress:
        activities = [item for item in self.activities if item.trainer_id == trainer_id]
        return AchievementProgress(
            capture_count=sum(
                item.activity_type is AchievementActivityType.CAPTURE
                for item in activities
            ),
            shiny_capture_count=sum(
                item.activity_type is AchievementActivityType.SHINY_CAPTURE
                for item in activities
            ),
            unique_discovered_species=sum(
                item.activity_type is AchievementActivityType.SPECIES_DISCOVERED
                for item in activities
            ),
            completed_trade_count=sum(
                item.activity_type is AchievementActivityType.COMPLETED_TRADE
                for item in activities
            ),
            safari_capture_count=sum(
                item.activity_type is AchievementActivityType.SAFARI_CAPTURE
                for item in activities
            ),
            evolution_count=sum(
                item.activity_type is AchievementActivityType.EVOLUTION
                for item in activities
            ),
        )


class FakeAchievementUnlockRepository(AchievementUnlockRepository):
    def __init__(self) -> None:
        self.inventory_by_trainer: dict[int, CandyInventory] = {}
        self.mints_by_trainer: dict[int, int] = {}
        self._unlocks: dict[tuple[int, str], AchievementUnlock] = {}

    async def get_by_trainer(self, trainer_id: int) -> tuple[AchievementUnlock, ...]:
        return tuple(
            unlock
            for (stored_trainer_id, _), unlock in self._unlocks.items()
            if stored_trainer_id == trainer_id
        )

    async def award(
        self,
        trainer_id: int,
        achievement_id: str,
        rewarded_candies: CandyBundle,
        unlocked_at: datetime,
        rewarded_mints: int = 0,
    ) -> bool:
        key = (trainer_id, achievement_id)
        if key in self._unlocks:
            return False
        self._unlocks[key] = AchievementUnlock(
            trainer_id=trainer_id,
            achievement_id=achievement_id,
            unlocked_at=unlocked_at.astimezone(UTC),
            rewarded_candies=rewarded_candies,
            rewarded_mints=rewarded_mints,
        )
        self.inventory_by_trainer.setdefault(trainer_id, CandyInventory()).add(
            rewarded_candies
        )
        self.mints_by_trainer[trainer_id] = (
            self.mints_by_trainer.get(trainer_id, 0) + rewarded_mints
        )
        return True
