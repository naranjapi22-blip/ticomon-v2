from abc import ABC, abstractmethod
from datetime import datetime

from core.achievement.activity import AchievementActivity
from core.trade.trade import Trade


class TradeRepository(ABC):
    """Persists trade negotiations and executes completed exchanges."""

    @abstractmethod
    async def save(self, trade: Trade) -> Trade:
        """Persists a draft or active trade and returns its stored state."""

    @abstractmethod
    async def get(self, trade_id: int) -> Trade | None:
        """Returns a trade by identifier, if it exists."""

    @abstractmethod
    async def execute_completed_trade(
        self,
        trade: Trade,
        completed_at: datetime,
        activities: tuple[AchievementActivity, ...] = (),
    ) -> Trade:
        """Atomically exchanges ownership and returns committed trade state.

        Concrete implementations must revalidate live ownership and persist
        both the ownership transfer and the completed trade in one operation.
        """
