import pytest

from core.achievement.definition import (
    ACHIEVEMENT_DEFINITIONS,
    AchievementCriterion,
    AchievementDefinition,
    AchievementId,
)


def test_mvp_definitions_have_stable_unique_ids() -> None:
    ids = {definition.id for definition in ACHIEVEMENT_DEFINITIONS}
    assert {
        AchievementId.FIRST_CAPTURE,
        AchievementId.CAPTURES_10,
        AchievementId.CAPTURES_50,
        AchievementId.FIRST_SHINY_CAPTURE,
        AchievementId.UNIQUE_SPECIES_10,
        AchievementId.FIRST_COMPLETED_TRADE,
        AchievementId.FIRST_SAFARI_CAPTURE,
    } <= ids
    assert len(ACHIEVEMENT_DEFINITIONS) == 60
    assert len(ids) == len(ACHIEVEMENT_DEFINITIONS)


def test_nature_mint_rewards_total_thirty_five_and_use_requested_milestones() -> None:
    rewards = {
        definition.id.value: definition.mint_reward
        for definition in ACHIEVEMENT_DEFINITIONS
        if definition.mint_reward
    }

    assert rewards == {
        "first_shiny_capture": 1,
        "first_legendary_capture": 1,
        "captures_25": 1,
        "captures_100": 1,
        "legendary_captures_5": 2,
        "legendary_captures_10": 2,
        "first_mythical_capture": 1,
        "mythical_captures_3": 2,
        "mythical_captures_5": 2,
        "first_evolution": 1,
        "unique_species_50": 1,
        "unique_species_100": 1,
        "unique_species_250": 2,
        "unique_species_500": 3,
        "shiny_captures_5": 2,
        "captures_500": 2,
        "captures_1000": 3,
        "safari_captures_10": 1,
        "safari_captures_50_milestone": 1,
        "safari_captures_250": 2,
        "safari_captures_50": 3,
    }
    assert sum(rewards.values()) == 35


def test_safari_captures_50_id_preserves_identity_but_means_500() -> None:
    definition = next(
        item
        for item in ACHIEVEMENT_DEFINITIONS
        if item.id is AchievementId.SAFARI_CAPTURES_50
    )

    assert definition.threshold == 500
    assert definition.mint_reward == 3


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
