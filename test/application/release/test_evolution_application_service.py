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
from core.evolution.evolution_unit_of_work import (
    EvolutionTransaction,
    EvolutionUnitOfWork,
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


class _AtomicEvolutionTransaction(EvolutionTransaction):
    def __init__(self, creature, inventory, *, fail_on_save=False):
        self.creature = creature
        self.inventory = inventory
        self.fail_on_save = fail_on_save
        self.updated = False
        self.saved = False

    async def get_creature(self, trainer_id, collection_number):
        return self.creature

    async def get_candy_inventory(self, trainer_id):
        return self.inventory

    async def update_creature(self, creature):
        self.updated = True
        return creature

    async def save_candy_inventory(self, trainer_id, inventory):
        if self.fail_on_save:
            raise RuntimeError("candy persistence failed")
        self.saved = True


class _AtomicEvolutionUnitOfWork(EvolutionUnitOfWork):
    def __init__(self, transaction):
        self.transaction_value = transaction

    class _Context:
        def __init__(self, transaction):
            self.transaction = transaction
            self.before_species = None
            self.before_candies = None

        async def __aenter__(self):
            self.before_species = self.transaction.creature.species
            self.before_candies = dict(self.transaction.inventory._candies)
            return self.transaction

        async def __aexit__(self, exc_type, exc, traceback):
            if exc_type is not None:
                self.transaction.creature.species = self.before_species
                self.transaction.inventory._candies = self.before_candies
            return False

    def transaction(self):
        return self._Context(self.transaction_value)


@pytest.mark.asyncio
async def test_evolution_unit_of_work_persists_creature_and_candies_together():
    first = SpeciesBuilder().with_id(1).build()
    second = SpeciesBuilder().with_id(2).build()
    creature = (
        CreatureBuilder()
        .with_id(7)
        .with_collection_number(1)
        .with_species(first)
        .build()
    )
    inventory = CandyInventory()
    inventory.add(CandyBundle.from_amounts(CandyAmount(CandyType.FIRE, 10)))
    transaction = _AtomicEvolutionTransaction(creature, inventory)
    rule = (
        EvolutionRuleBuilder()
        .with_from_species(1)
        .with_to_species(2)
        .with_candy_type(CandyType.FIRE)
        .with_tier("basic")
        .build()
    )
    service = EvolutionApplicationService(
        EvolutionService(
            policy=EvolutionPolicy(cost_policy=EvolutionCostPolicy()),
            species_repository=FakeSpeciesRepository(first, second),
        ),
        evolution_repository=FakeEvolutionRepository(rule),
        creature_repository=FakeCreatureRepository(creature),
        candy_repository=FakeCandyRepository(inventory),
        evolution_unit_of_work=_AtomicEvolutionUnitOfWork(transaction),
    )

    result = await service.evolve(1, 1, rule)

    assert result.success
    assert transaction.updated
    assert transaction.saved


@pytest.mark.asyncio
async def test_evolution_unit_of_work_propagates_candy_failure_before_commit():
    first = SpeciesBuilder().with_id(1).build()
    second = SpeciesBuilder().with_id(2).build()
    creature = CreatureBuilder().with_id(7).with_species(first).build()
    inventory = CandyInventory()
    inventory.add(CandyBundle.from_amounts(CandyAmount(CandyType.FIRE, 10)))
    transaction = _AtomicEvolutionTransaction(creature, inventory, fail_on_save=True)
    rule = (
        EvolutionRuleBuilder()
        .with_from_species(1)
        .with_to_species(2)
        .with_candy_type(CandyType.FIRE)
        .with_tier("basic")
        .build()
    )
    service = EvolutionApplicationService(
        EvolutionService(
            policy=EvolutionPolicy(cost_policy=EvolutionCostPolicy()),
            species_repository=FakeSpeciesRepository(first, second),
        ),
        evolution_repository=FakeEvolutionRepository(rule),
        creature_repository=FakeCreatureRepository(creature),
        candy_repository=FakeCandyRepository(inventory),
        evolution_unit_of_work=_AtomicEvolutionUnitOfWork(transaction),
    )

    with pytest.raises(RuntimeError, match="candy persistence failed"):
        await service.evolve(1, 1, rule)

    assert transaction.updated
    assert not transaction.saved
    assert creature.species is first
    assert inventory.get_amount(CandyType.FIRE) == 10


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
