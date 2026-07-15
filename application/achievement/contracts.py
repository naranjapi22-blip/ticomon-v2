from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from core.achievement.activity import AchievementActivity
from core.candy.candy_bundle import CandyBundle


@dataclass(frozen=True, slots=True)
class AchievementProgress:
    capture_count: int
    shiny_capture_count: int
    unique_discovered_species: int
    completed_trade_count: int
    safari_capture_count: int


@dataclass(frozen=True, slots=True)
class AchievementUnlock:
    trainer_id: int
    achievement_id: str
    unlocked_at: datetime
    rewarded_candies: CandyBundle


class AchievementActivityRepository(ABC):
    @abstractmethod
    async def record(self, activity: AchievementActivity) -> bool:
        """Records a historical action and returns whether it was newly inserted."""

    @abstractmethod
    async def get_progress(self, trainer_id: int) -> AchievementProgress:
        """Returns historical metrics derived from immutable activities."""


class AchievementUnlockRepository(ABC):
    @abstractmethod
    async def get_by_trainer(self, trainer_id: int) -> tuple[AchievementUnlock, ...]:
        """Returns already awarded achievements without side effects."""

    @abstractmethod
    async def award(
        self,
        trainer_id: int,
        achievement_id: str,
        rewarded_candies: CandyBundle,
        unlocked_at: datetime,
    ) -> bool:
        """Atomically records an unlock and adds its candies once."""
