import pytest

from core.achievement.definition import (
    ACHIEVEMENT_DEFINITIONS,
    AchievementCriterion,
    AchievementDefinition,
    AchievementId,
)


def test_mvp_definitions_have_stable_unique_ids() -> None:
    assert {definition.id for definition in ACHIEVEMENT_DEFINITIONS} == {
        AchievementId.FIRST_CAPTURE,
        AchievementId.CAPTURES_10,
        AchievementId.CAPTURES_50,
        AchievementId.FIRST_SHINY_CAPTURE,
        AchievementId.UNIQUE_SPECIES_10,
        AchievementId.FIRST_COMPLETED_TRADE,
        AchievementId.FIRST_SAFARI_CAPTURE,
    }


def test_definition_rejects_invalid_threshold_or_reward() -> None:
    with pytest.raises(ValueError):
        AchievementDefinition(
            AchievementId.FIRST_CAPTURE,
            AchievementCriterion.CAPTURE_COUNT,
            threshold=0,
            reward_amount=2,
        )

    with pytest.raises(ValueError):
        AchievementDefinition(
            AchievementId.FIRST_CAPTURE,
            AchievementCriterion.CAPTURE_COUNT,
            threshold=1,
            reward_amount=3,
        )
