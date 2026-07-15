from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AchievementActivityType(StrEnum):
    CAPTURE = "capture"
    SHINY_CAPTURE = "shiny_capture"
    SPECIES_DISCOVERED = "species_discovered"
    EVOLUTION = "evolution"
    RELEASE = "release"
    COMPLETED_TRADE = "completed_trade"
    SAFARI_PARTICIPATION = "safari_participation"
    SAFARI_CAPTURE = "safari_capture"


class AchievementSource(StrEnum):
    NORMAL = "normal"
    SAFARI = "safari"


@dataclass(frozen=True, slots=True)
class AchievementActivity:
    trainer_id: int
    activity_type: AchievementActivityType
    idempotency_key: str
    species_id: int | None = None
    source: AchievementSource | None = None
    occurred_at: datetime | None = None
