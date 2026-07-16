import pytest

from application.achievement.award_service import CaptureAchievementAwardService
from core.achievement.activity import AchievementActivity, AchievementActivityType
from core.candy.candy_type import CandyType
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_achievement_repositories import (
    FakeAchievementActivityRepository,
    FakeAchievementUnlockRepository,
)


async def _record_capture(repository, trainer_id, number, species_id):
    key = f"creature:{number}"
    await repository.record(
        AchievementActivity(
            trainer_id,
            AchievementActivityType.CAPTURE,
            key,
            species_id,
        )
    )


@pytest.mark.asyncio
async def test_first_capture_awards_species_candies_once():
    activities = FakeAchievementActivityRepository()
    unlocks = FakeAchievementUnlockRepository()
    species = SpeciesBuilder().with_types(["fire", "water"]).build()
    await _record_capture(activities, 1, 1, species.id)
    service = CaptureAchievementAwardService(activities, unlocks)

    first = await service.award_for_capture(1, species, is_shiny=False, is_safari=False)
    retry = await service.award_for_capture(1, species, is_shiny=False, is_safari=False)

    assert [unlock.achievement_id for unlock in first] == ["first_capture"]
    assert retry == ()
    inventory = unlocks.inventory_by_trainer[1]
    assert inventory.get_amount(CandyType.FIRE) == 1
    assert inventory.get_amount(CandyType.WATER) == 1


@pytest.mark.asyncio
async def test_capture_milestones_and_safari_award_only_affected_definitions():
    activities = FakeAchievementActivityRepository()
    unlocks = FakeAchievementUnlockRepository()
    species = SpeciesBuilder().with_types(["grass"]).build()
    for number in range(1, 11):
        await _record_capture(activities, 1, number, species.id)
    await activities.record(
        AchievementActivity(1, AchievementActivityType.SAFARI_CAPTURE, "creature:10")
    )
    service = CaptureAchievementAwardService(activities, unlocks)

    awarded = await service.award_for_capture(
        1,
        species,
        is_shiny=False,
        is_safari=True,
    )

    assert {unlock.achievement_id for unlock in awarded} == {
        "first_capture",
        "captures_10",
        "first_safari_capture",
    }


@pytest.mark.asyncio
async def test_first_shiny_awards_one_nature_mint_separately():
    activities = FakeAchievementActivityRepository()
    unlocks = FakeAchievementUnlockRepository()
    species = SpeciesBuilder().with_types(["grass"]).build()
    await activities.record(
        AchievementActivity(
            1,
            AchievementActivityType.CAPTURE,
            "creature:1",
            species.id,
        )
    )
    await activities.record(
        AchievementActivity(
            1,
            AchievementActivityType.SHINY_CAPTURE,
            "creature:1",
            species.id,
        )
    )

    awarded = await CaptureAchievementAwardService(
        activities, unlocks
    ).award_for_capture(1, species, is_shiny=True, is_safari=False)

    shiny = next(
        item for item in awarded if item.achievement_id == "first_shiny_capture"
    )
    assert shiny.rewarded_mints == 1
    assert unlocks.mints_by_trainer[1] == 1


@pytest.mark.asyncio
async def test_first_completed_trade_awards_once_with_offered_species_types():
    activities = FakeAchievementActivityRepository()
    unlocks = FakeAchievementUnlockRepository()
    species = SpeciesBuilder().with_types(["fire", "water"]).build()
    await activities.record(
        AchievementActivity(1, AchievementActivityType.COMPLETED_TRADE, "trade:1")
    )
    service = CaptureAchievementAwardService(activities, unlocks)

    awarded = await service.award_for_completed_trade(1, species)
    retry = await service.award_for_completed_trade(1, species)

    assert [unlock.achievement_id for unlock in awarded] == ["first_completed_trade"]
    assert retry == ()
    inventory = unlocks.inventory_by_trainer[1]
    assert inventory.get_amount(CandyType.FIRE) == 2
    assert inventory.get_amount(CandyType.WATER) == 2
