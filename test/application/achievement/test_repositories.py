from datetime import UTC, datetime

import pytest

from application.achievement.contracts import (
    AchievementActivity,
    AchievementActivityType,
)
from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from test.fakes.fake_achievement_repositories import (
    FakeAchievementActivityRepository,
    FakeAchievementUnlockRepository,
)

NOW = datetime(2026, 7, 15, tzinfo=UTC)


@pytest.mark.asyncio
async def test_records_activity_and_ignores_a_retry() -> None:
    repository = FakeAchievementActivityRepository()
    activity = AchievementActivity(
        trainer_id=1,
        activity_type=AchievementActivityType.CAPTURE,
        species_id=25,
        idempotency_key="creature:100",
    )

    assert await repository.record(activity) is True
    assert await repository.record(activity) is False
    assert (await repository.get_progress(1)).capture_count == 1


@pytest.mark.asyncio
async def test_same_activity_key_is_independent_per_trainer() -> None:
    repository = FakeAchievementActivityRepository()

    for trainer_id in (1, 2):
        assert await repository.record(
            AchievementActivity(
                trainer_id=trainer_id,
                activity_type=AchievementActivityType.CAPTURE,
                species_id=25,
                idempotency_key="creature:100",
            )
        )

    assert (await repository.get_progress(1)).capture_count == 1
    assert (await repository.get_progress(2)).capture_count == 1


@pytest.mark.asyncio
async def test_same_species_is_discovered_once_even_from_distinct_captures() -> None:
    repository = FakeAchievementActivityRepository()

    first = AchievementActivity(
        trainer_id=1,
        activity_type=AchievementActivityType.SPECIES_DISCOVERED,
        species_id=25,
        idempotency_key="creature:100",
    )
    second = AchievementActivity(
        trainer_id=1,
        activity_type=AchievementActivityType.SPECIES_DISCOVERED,
        species_id=25,
        idempotency_key="creature:101",
    )

    assert await repository.record(first) is True
    assert await repository.record(second) is False
    assert (await repository.get_progress(1)).unique_discovered_species == 1


@pytest.mark.asyncio
async def test_progress_counts_capture_species_and_shiny_facts() -> None:
    repository = FakeAchievementActivityRepository()
    activities = (
        (AchievementActivityType.CAPTURE, 1, "capture:1"),
        (AchievementActivityType.CAPTURE, 2, "capture:2"),
        (AchievementActivityType.SHINY_CAPTURE, 2, "capture:2"),
        (AchievementActivityType.SPECIES_DISCOVERED, 1, "capture:1"),
        (AchievementActivityType.SPECIES_DISCOVERED, 2, "capture:2"),
    )
    for activity_type, species_id, key in activities:
        await repository.record(
            AchievementActivity(
                trainer_id=1,
                activity_type=activity_type,
                species_id=species_id,
                idempotency_key=key,
            )
        )

    progress = await repository.get_progress(1)

    assert progress.capture_count == 2
    assert progress.shiny_capture_count == 1
    assert progress.unique_discovered_species == 2


@pytest.mark.asyncio
async def test_award_is_idempotent_and_preserves_exact_reward() -> None:
    repository = FakeAchievementUnlockRepository()
    reward = CandyBundle.from_amounts(
        CandyAmount(CandyType.FIRE, 2),
        CandyAmount(CandyType.FLYING, 2),
    )

    assert await repository.award(1, "first_capture", reward, NOW) is True
    assert await repository.award(1, "first_capture", reward, NOW) is False

    unlocks = await repository.get_by_trainer(1)
    assert unlocks[0].rewarded_candies == reward
    assert repository.inventory_by_trainer[1].get_amount(CandyType.FIRE) == 2
    assert repository.inventory_by_trainer[1].get_amount(CandyType.FLYING) == 2


@pytest.mark.asyncio
async def test_two_achievements_are_awarded_once_each() -> None:
    repository = FakeAchievementUnlockRepository()
    reward = CandyBundle.from_amounts(CandyAmount(CandyType.WATER, 4))

    assert await repository.award(1, "first_capture", reward, NOW)
    assert await repository.award(1, "captures_10", reward, NOW)

    assert {unlock.achievement_id for unlock in await repository.get_by_trainer(1)} == {
        "first_capture",
        "captures_10",
    }
    assert repository.inventory_by_trainer[1].get_amount(CandyType.WATER) == 8
