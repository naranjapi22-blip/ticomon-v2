from dataclasses import dataclass
from enum import StrEnum


class AchievementId(StrEnum):
    FIRST_CAPTURE = "first_capture"
    CAPTURES_10 = "captures_10"
    CAPTURES_50 = "captures_50"
    FIRST_SHINY_CAPTURE = "first_shiny_capture"
    UNIQUE_SPECIES_10 = "unique_species_10"
    FIRST_COMPLETED_TRADE = "first_completed_trade"
    FIRST_SAFARI_CAPTURE = "first_safari_capture"


class AchievementCriterion(StrEnum):
    CAPTURE_COUNT = "capture_count"
    SHINY_CAPTURE_COUNT = "shiny_capture_count"
    UNIQUE_DISCOVERED_SPECIES = "unique_discovered_species"
    COMPLETED_TRADE_COUNT = "completed_trade_count"
    SAFARI_CAPTURE_COUNT = "safari_capture_count"


@dataclass(frozen=True, slots=True)
class AchievementDefinition:
    id: AchievementId
    criterion: AchievementCriterion
    threshold: int
    reward_amount: int

    def __post_init__(self) -> None:
        if self.threshold <= 0:
            raise ValueError("Achievement threshold must be positive.")
        if self.reward_amount <= 0 or self.reward_amount % 2:
            raise ValueError(
                "Achievement reward amount must be a positive even number."
            )


ACHIEVEMENT_DEFINITIONS: tuple[AchievementDefinition, ...] = (
    AchievementDefinition(
        AchievementId.FIRST_CAPTURE,
        AchievementCriterion.CAPTURE_COUNT,
        threshold=1,
        reward_amount=2,
    ),
    AchievementDefinition(
        AchievementId.CAPTURES_10,
        AchievementCriterion.CAPTURE_COUNT,
        threshold=10,
        reward_amount=4,
    ),
    AchievementDefinition(
        AchievementId.CAPTURES_50,
        AchievementCriterion.CAPTURE_COUNT,
        threshold=50,
        reward_amount=10,
    ),
    AchievementDefinition(
        AchievementId.FIRST_SHINY_CAPTURE,
        AchievementCriterion.SHINY_CAPTURE_COUNT,
        threshold=1,
        reward_amount=6,
    ),
    AchievementDefinition(
        AchievementId.UNIQUE_SPECIES_10,
        AchievementCriterion.UNIQUE_DISCOVERED_SPECIES,
        threshold=10,
        reward_amount=6,
    ),
    AchievementDefinition(
        AchievementId.FIRST_COMPLETED_TRADE,
        AchievementCriterion.COMPLETED_TRADE_COUNT,
        threshold=1,
        reward_amount=4,
    ),
    AchievementDefinition(
        AchievementId.FIRST_SAFARI_CAPTURE,
        AchievementCriterion.SAFARI_CAPTURE_COUNT,
        threshold=1,
        reward_amount=4,
    ),
)
