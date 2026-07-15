from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from core.achievement.unlock_result import AchievementUnlockResult
from core.trade.trade import Trade


@dataclass(frozen=True, slots=True)
class AcceptTradeResult:
    trade: Trade
    achievements_by_trainer: Mapping[int, tuple[AchievementUnlockResult, ...]] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __getattr__(self, name):
        return getattr(self.trade, name)
