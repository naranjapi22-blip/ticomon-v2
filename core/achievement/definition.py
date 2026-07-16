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

    CAPTURES_100 = "captures_100"
    CAPTURES_250 = "captures_250"
    CAPTURES_500 = "captures_500"
    CAPTURES_1000 = "captures_1000"
    UNIQUE_SPECIES_25 = "unique_species_25"
    UNIQUE_SPECIES_50 = "unique_species_50"
    UNIQUE_SPECIES_100 = "unique_species_100"
    UNIQUE_SPECIES_250 = "unique_species_250"
    UNIQUE_SPECIES_500 = "unique_species_500"
    SHINY_CAPTURES_5 = "shiny_captures_5"
    SHINY_CAPTURES_10 = "shiny_captures_10"
    SHINY_CAPTURES_25 = "shiny_captures_25"
    SHINY_CAPTURES_50 = "shiny_captures_50"
    SHINY_CAPTURES_100 = "shiny_captures_100"
    SAFARI_CAPTURES_10 = "safari_captures_10"
    SAFARI_CAPTURES_25 = "safari_captures_25"
    SAFARI_CAPTURES_50 = "safari_captures_50"
    SAFARI_CAPTURES_100 = "safari_captures_100"
    COMPLETED_TRADES_10 = "completed_trades_10"
    COMPLETED_TRADES_25 = "completed_trades_25"
    COMPLETED_TRADES_50 = "completed_trades_50"
    COMPLETED_TRADES_100 = "completed_trades_100"
    FIRST_LEGENDARY_CAPTURE = "first_legendary_capture"
    LEGENDARY_CAPTURES_5 = "legendary_captures_5"
    LEGENDARY_CAPTURES_10 = "legendary_captures_10"
    FIRST_MYTHICAL_CAPTURE = "first_mythical_capture"
    MYTHICAL_CAPTURES_3 = "mythical_captures_3"
    MYTHICAL_CAPTURES_5 = "mythical_captures_5"
    FIRST_BABY_CAPTURE = "first_baby_capture"
    BABY_CAPTURES_5 = "baby_captures_5"
    BABY_CAPTURES_10 = "baby_captures_10"
    NORMAL_CAPTURES_25 = "normal_captures_25"
    FIRE_CAPTURES_25 = "fire_captures_25"
    WATER_CAPTURES_25 = "water_captures_25"
    ELECTRIC_CAPTURES_25 = "electric_captures_25"
    GRASS_CAPTURES_25 = "grass_captures_25"
    ICE_CAPTURES_25 = "ice_captures_25"
    FIGHTING_CAPTURES_25 = "fighting_captures_25"
    POISON_CAPTURES_25 = "poison_captures_25"
    GROUND_CAPTURES_25 = "ground_captures_25"
    FLYING_CAPTURES_25 = "flying_captures_25"
    PSYCHIC_CAPTURES_25 = "psychic_captures_25"
    BUG_CAPTURES_25 = "bug_captures_25"
    ROCK_CAPTURES_25 = "rock_captures_25"
    GHOST_CAPTURES_25 = "ghost_captures_25"
    DRAGON_CAPTURES_25 = "dragon_captures_25"
    DARK_CAPTURES_25 = "dark_captures_25"
    STEEL_CAPTURES_25 = "steel_captures_25"
    FAIRY_CAPTURES_25 = "fairy_captures_25"


class AchievementCriterion(StrEnum):
    CAPTURE_COUNT = "capture_count"
    SHINY_CAPTURE_COUNT = "shiny_capture_count"
    UNIQUE_DISCOVERED_SPECIES = "unique_discovered_species"
    COMPLETED_TRADE_COUNT = "completed_trade_count"
    SAFARI_CAPTURE_COUNT = "safari_capture_count"
    LEGENDARY_CAPTURE_COUNT = "legendary_capture_count"
    MYTHICAL_CAPTURE_COUNT = "mythical_capture_count"
    BABY_CAPTURE_COUNT = "baby_capture_count"
    TYPE_CAPTURE_COUNT = "type_capture_count"


@dataclass(frozen=True, slots=True)
class AchievementDefinition:
    id: AchievementId
    criterion: AchievementCriterion
    threshold: int
    reward_amount: int
    scope: str | None = None
    mint_reward: int = 0

    def __post_init__(self) -> None:
        if self.threshold <= 0:
            raise ValueError("Achievement threshold must be positive.")
        if self.reward_amount <= 0 or self.reward_amount % 2:
            raise ValueError(
                "Achievement reward amount must be a positive even number."
            )
        if self.mint_reward < 0:
            raise ValueError("Achievement mint reward cannot be negative.")


_BASE_DEFINITIONS: tuple[AchievementDefinition, ...] = (
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
        mint_reward=1,
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


def _milestones(
    prefix: str, criterion: AchievementCriterion, values: tuple[tuple[int, int], ...]
):
    return tuple(
        AchievementDefinition(
            getattr(AchievementId, f"{prefix}_{threshold}".upper()),
            criterion,
            threshold,
            reward,
        )
        for threshold, reward in values
    )


ACHIEVEMENT_DEFINITIONS = _BASE_DEFINITIONS + (
    *_milestones(
        "CAPTURES",
        AchievementCriterion.CAPTURE_COUNT,
        ((100, 20), (250, 30), (500, 50), (1000, 100)),
    ),
    *_milestones(
        "UNIQUE_SPECIES",
        AchievementCriterion.UNIQUE_DISCOVERED_SPECIES,
        ((25, 10), (50, 16), (100, 24), (250, 40), (500, 70)),
    ),
    *_milestones(
        "SHINY_CAPTURES",
        AchievementCriterion.SHINY_CAPTURE_COUNT,
        ((5, 10), (10, 16), (25, 30), (50, 50), (100, 90)),
    ),
    *_milestones(
        "SAFARI_CAPTURES",
        AchievementCriterion.SAFARI_CAPTURE_COUNT,
        ((10, 8), (25, 16), (50, 30), (100, 60)),
    ),
    *_milestones(
        "COMPLETED_TRADES",
        AchievementCriterion.COMPLETED_TRADE_COUNT,
        ((10, 8), (25, 16), (50, 30), (100, 60)),
    ),
    AchievementDefinition(
        AchievementId.FIRST_LEGENDARY_CAPTURE,
        AchievementCriterion.LEGENDARY_CAPTURE_COUNT,
        1,
        6,
        mint_reward=1,
    ),
    AchievementDefinition(
        AchievementId.LEGENDARY_CAPTURES_5,
        AchievementCriterion.LEGENDARY_CAPTURE_COUNT,
        5,
        16,
        mint_reward=1,
    ),
    AchievementDefinition(
        AchievementId.LEGENDARY_CAPTURES_10,
        AchievementCriterion.LEGENDARY_CAPTURE_COUNT,
        10,
        30,
    ),
    AchievementDefinition(
        AchievementId.FIRST_MYTHICAL_CAPTURE,
        AchievementCriterion.MYTHICAL_CAPTURE_COUNT,
        1,
        6,
        mint_reward=1,
    ),
    AchievementDefinition(
        AchievementId.MYTHICAL_CAPTURES_3,
        AchievementCriterion.MYTHICAL_CAPTURE_COUNT,
        3,
        12,
        mint_reward=1,
    ),
    AchievementDefinition(
        AchievementId.MYTHICAL_CAPTURES_5,
        AchievementCriterion.MYTHICAL_CAPTURE_COUNT,
        5,
        24,
    ),
    AchievementDefinition(
        AchievementId.FIRST_BABY_CAPTURE, AchievementCriterion.BABY_CAPTURE_COUNT, 1, 4
    ),
    AchievementDefinition(
        AchievementId.BABY_CAPTURES_5, AchievementCriterion.BABY_CAPTURE_COUNT, 5, 12
    ),
    AchievementDefinition(
        AchievementId.BABY_CAPTURES_10, AchievementCriterion.BABY_CAPTURE_COUNT, 10, 24
    ),
    AchievementDefinition(
        AchievementId.NORMAL_CAPTURES_25,
        AchievementCriterion.TYPE_CAPTURE_COUNT,
        25,
        10,
        "normal",
    ),
    *(
        AchievementDefinition(
            AchievementId[f"{kind.upper()}_CAPTURES_25"],
            AchievementCriterion.TYPE_CAPTURE_COUNT,
            25,
            10,
            kind,
        )
        for kind in (
            "fire",
            "water",
            "electric",
            "grass",
            "ice",
            "fighting",
            "poison",
            "ground",
            "flying",
            "psychic",
            "bug",
            "rock",
            "ghost",
            "dragon",
            "dark",
            "steel",
            "fairy",
        )
    ),
)
