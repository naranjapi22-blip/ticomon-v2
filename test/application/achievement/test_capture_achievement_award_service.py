import pytest

from application.achievement.award_service import CaptureAchievementAwardService
from application.achievement.contracts import AchievementProgress
from core.achievement.activity import AchievementActivity, AchievementActivityType
from core.candy.candy_type import CandyType
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_achievement_repositories import (
    FakeAchievementActivityRepository,
    FakeAchievementUnlockRepository,
)


class _StaticProgressRepository:
    def __init__(self, progress: AchievementProgress) -> None:
        self.progress = progress

    async def get_progress(self, trainer_id: int) -> AchievementProgress:
        return self.progress


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "criterion",
        "threshold",
        "achievement_id",
        "mint_reward",
        "is_shiny",
        "is_safari",
    ),
    (
        ("capture_count", 25, "captures_25", 1, False, False),
        ("unique_discovered_species", 50, "unique_species_50", 1, False, False),
        ("safari_capture_count", 10, "safari_captures_10", 1, False, True),
        ("capture_count", 100, "captures_100", 1, False, False),
        ("unique_discovered_species", 100, "unique_species_100", 1, False, False),
        (
            "safari_capture_count",
            50,
            "safari_captures_50_milestone",
            1,
            False,
            True,
        ),
        ("shiny_capture_count", 5, "shiny_captures_5", 2, True, False),
        ("legendary_capture_count", 10, "legendary_captures_10", 2, False, False),
        ("mythical_capture_count", 5, "mythical_captures_5", 2, False, False),
        ("unique_discovered_species", 250, "unique_species_250", 2, False, False),
        ("unique_discovered_species", 500, "unique_species_500", 3, False, False),
        ("capture_count", 500, "captures_500", 2, False, False),
        ("capture_count", 1000, "captures_1000", 3, False, False),
        ("safari_capture_count", 250, "safari_captures_250", 2, False, True),
        ("safari_capture_count", 500, "safari_captures_50", 3, False, True),
    ),
)
async def test_new_nature_mint_milestone_rewards(
    criterion: str,
    threshold: int,
    achievement_id: str,
    mint_reward: int,
    is_shiny: bool,
    is_safari: bool,
):
    progress = AchievementProgress(
        capture_count=threshold if criterion == "capture_count" else 0,
        shiny_capture_count=threshold if criterion == "shiny_capture_count" else 0,
        unique_discovered_species=(
            threshold if criterion == "unique_discovered_species" else 0
        ),
        completed_trade_count=0,
        safari_capture_count=threshold if criterion == "safari_capture_count" else 0,
        legendary_capture_count=(
            threshold if criterion == "legendary_capture_count" else 0
        ),
        mythical_capture_count=(
            threshold if criterion == "mythical_capture_count" else 0
        ),
    )
    activities = _StaticProgressRepository(progress)
    unlocks = FakeAchievementUnlockRepository()
    species = SpeciesBuilder().with_types(["grass"]).build()

    awarded = await CaptureAchievementAwardService(
        activities, unlocks
    ).award_for_capture(1, species, is_shiny=is_shiny, is_safari=is_safari)

    result = next(item for item in awarded if item.achievement_id == achievement_id)
    assert result.rewarded_mints == mint_reward
    assert unlocks.mints_by_trainer[1] >= mint_reward


@pytest.mark.asyncio
async def test_first_evolution_awards_one_mint_once() -> None:
    activities = FakeAchievementActivityRepository()
    unlocks = FakeAchievementUnlockRepository()
    species = SpeciesBuilder().with_types(["grass"]).build()
    activity = AchievementActivity(
        1, AchievementActivityType.EVOLUTION, "evolution:7:2", species.id
    )
    assert await activities.record(activity) is True

    service = CaptureAchievementAwardService(activities, unlocks)
    awarded = await service.award_for_evolution(1, species)
    retry = await service.award_for_evolution(1, species)

    assert [item.achievement_id for item in awarded] == ["first_evolution"]
    assert awarded[0].rewarded_mints == 1
    assert retry == ()
    assert unlocks.mints_by_trainer[1] == 1
