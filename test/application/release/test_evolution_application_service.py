import pytest

from application.achievement.award_service import CaptureAchievementAwardService
from application.evolution.evolution_application_service import (
    EvolutionApplicationService,
)
from core.achievement.activity import AchievementActivityType
from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.creature.nature import Nature
from core.evolution.evolution_cost_policy import (
    EvolutionCostPolicy,
)
from core.evolution.evolution_policy import (
    EvolutionPolicy,
)
from core.evolution.evolution_service import (
    EvolutionService,
)
from test.builders.creature_builder import (
    CreatureBuilder,
)
from test.builders.evolution_rule_builder import (
    EvolutionRuleBuilder,
)
from test.builders.species_builder import (
    SpeciesBuilder,
)
from test.fakes.fake_achievement_repositories import (
    FakeAchievementActivityRepository,
    FakeAchievementUnlockRepository,
)
from test.fakes.fake_candy_repository import (
    FakeCandyRepository,
)
from test.fakes.fake_collection_history_repository import (
    FakeCollectionHistoryRepository,
)
from test.fakes.fake_creature_repository import (
    FakeCreatureRepository,
)
from test.fakes.fake_evolution_repository import (
    FakeEvolutionRepository,
)
from test.fakes.fake_species_repository import (
    FakeSpeciesRepository,
)


@pytest.mark.asyncio
async def test_evolution_application_service_evolves_creature():

    first_species = SpeciesBuilder().with_id(1).build()

    second_species = SpeciesBuilder().with_id(2).build()

    creature = (
        CreatureBuilder()
        .with_id(7)
        .with_trainer_id(113100351531417600)
        .with_collection_number(1)
        .shiny()
        .with_species(
            first_species,
        )
        .build()
    )
    creature.minted_nature = Nature("adamant")

    creature_repository = FakeCreatureRepository(
        creature,
    )

    inventory = CandyInventory()

    inventory.add(
        CandyBundle.from_amounts(
            CandyAmount(
                CandyType.FIRE,
                10,
            )
        )
    )

    candy_repository = FakeCandyRepository(
        inventory,
    )

    rule = (
        EvolutionRuleBuilder()
        .with_from_species(
            1,
        )
        .with_to_species(
            2,
        )
        .with_candy_type(
            CandyType.FIRE,
        )
        .with_tier(
            "basic",
        )
        .build()
    )

    species_repository = FakeSpeciesRepository(
        first_species,
        second_species,
    )

    evolution_repository = FakeEvolutionRepository(
        rule,
    )
    achievement_activities = FakeAchievementActivityRepository()
    achievement_unlocks = FakeAchievementUnlockRepository()
    collection_history = FakeCollectionHistoryRepository()

    service = EvolutionApplicationService(
        EvolutionService(
            policy=EvolutionPolicy(
                cost_policy=EvolutionCostPolicy(),
            ),
            species_repository=species_repository,
        ),
        evolution_repository=evolution_repository,
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        achievement_activity_repository=achievement_activities,
        achievement_award_service=CaptureAchievementAwardService(
            achievement_activities,
            achievement_unlocks,
        ),
        collection_history_repository=collection_history,
    )

    result = await service.evolve(
        trainer_id=113100351531417600,
        collection_number=1,
        rule=rule,
    )
    assert result.success

    assert result.creature.species.id == 2
    assert result.creature.collection_number == 1
    assert result.creature.id == 7
    assert result.creature.is_shiny is True
    assert result.creature.nature == Nature("hardy")
    assert result.creature.minted_nature == Nature("adamant")

    assert result.evolved_species.id == 2

    assert (
        inventory.get_amount(
            CandyType.FIRE,
        )
        == 0
    )

    assert (
        len(
            creature_repository.updated,
        )
        == 1
    )

    assert (
        len(
            candy_repository.saved,
        )
        == 1
    )
    assert [
        activity.activity_type for activity in achievement_activities.activities
    ] == [AchievementActivityType.EVOLUTION]
    assert achievement_activities.activities[0].idempotency_key == "evolution:7:2"
    assert [
        unlock.achievement_id
        for unlock in await achievement_unlocks.get_by_trainer(113100351531417600)
    ] == ["first_evolution"]
    assert achievement_unlocks.mints_by_trainer[113100351531417600] == 1
    history = await collection_history.entries_for_trainer(113100351531417600)
    assert [(entry.species_id, entry.source.value) for entry in history] == [
        (2, "evolution")
    ]
    retry = await service.evolve(113100351531417600, 1, rule)
    assert not retry.success
    assert len(achievement_activities.activities) == 1
    assert achievement_unlocks.mints_by_trainer[113100351531417600] == 1


@pytest.mark.asyncio
async def test_failed_evolution_does_not_record_achievement_activity():
    first_species = SpeciesBuilder().with_id(1).build()
    second_species = SpeciesBuilder().with_id(2).build()
    creature = (
        CreatureBuilder()
        .with_id(7)
        .with_collection_number(1)
        .with_species(first_species)
        .build()
    )
    creature_repository = FakeCreatureRepository(creature)
    candy_repository = FakeCandyRepository()
    rule = (
        EvolutionRuleBuilder()
        .with_from_species(1)
        .with_to_species(2)
        .with_candy_type(CandyType.FIRE)
        .build()
    )
    activities = FakeAchievementActivityRepository()
    unlocks = FakeAchievementUnlockRepository()
    service = EvolutionApplicationService(
        EvolutionService(
            policy=EvolutionPolicy(cost_policy=EvolutionCostPolicy()),
            species_repository=FakeSpeciesRepository(first_species, second_species),
        ),
        evolution_repository=FakeEvolutionRepository(rule),
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        achievement_activity_repository=activities,
        achievement_award_service=CaptureAchievementAwardService(activities, unlocks),
    )

    result = await service.evolve(1, 1, rule)

    assert not result.success
    assert activities.activities == []
    assert creature_repository.updated == []


@pytest.mark.asyncio
async def test_achievement_failure_does_not_revert_persisted_evolution():
    first_species = SpeciesBuilder().with_id(1).build()
    second_species = SpeciesBuilder().with_id(2).build()
    creature = (
        CreatureBuilder()
        .with_id(7)
        .with_collection_number(1)
        .with_species(first_species)
        .build()
    )
    creature_repository = FakeCreatureRepository(creature)
    inventory = CandyInventory()
    inventory.add(CandyBundle.from_amounts(CandyAmount(CandyType.FIRE, 10)))
    candy_repository = FakeCandyRepository(inventory)
    rule = (
        EvolutionRuleBuilder()
        .with_from_species(1)
        .with_to_species(2)
        .with_candy_type(CandyType.FIRE)
        .build()
    )
    activities = FakeAchievementActivityRepository()

    class FailingAwardService:
        async def award_for_evolution(self, trainer_id, species):
            raise RuntimeError("achievement storage unavailable")

    service = EvolutionApplicationService(
        EvolutionService(
            policy=EvolutionPolicy(cost_policy=EvolutionCostPolicy()),
            species_repository=FakeSpeciesRepository(first_species, second_species),
        ),
        evolution_repository=FakeEvolutionRepository(rule),
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        achievement_activity_repository=activities,
        achievement_award_service=FailingAwardService(),
    )

    result = await service.evolve(1, 1, rule)

    assert result.success
    assert creature_repository.updated
    assert len(activities.activities) == 1
