from contextlib import asynccontextmanager

import pytest

from application.release.preview_release_application_service import (
    PreviewReleaseApplicationService,
)
from application.release.release_application_service import (
    ReleaseApplicationService,
)
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.candy.reward_policy import RewardPolicy
from core.evolution.evolution_chain import EvolutionChain
from test.builders.creature_builder import CreatureBuilder
from test.builders.species_builder import SpeciesBuilder
from test.fakes.fake_candy_repository import FakeCandyRepository
from test.fakes.fake_creature_repository import FakeCreatureRepository


class _FailingRewardPolicy:
    def __init__(self):
        self.calls = 0

    def reward_for(self, creature):
        self.calls += 1
        if self.calls == 2:
            raise ValueError("reward calculation failed")
        return RewardPolicy().reward_for(creature)


class _AtomicReleaseUnitOfWork:
    def __init__(self, *creatures, fail_on_save=False):
        self.creatures = list(creatures)
        self.inventory = CandyInventory()
        self.fail_on_save = fail_on_save

    @asynccontextmanager
    async def transaction(self):
        original_creatures = list(self.creatures)
        original_inventory = dict(self.inventory._candies)
        transaction = _AtomicReleaseTransaction(self)
        try:
            yield transaction
        except Exception:
            self.creatures = original_creatures
            self.inventory = CandyInventory(original_inventory)
            raise


class _AtomicReleaseTransaction:
    def __init__(self, unit_of_work):
        self._unit_of_work = unit_of_work

    async def get_creatures_by_collection_numbers(self, trainer_id, numbers):
        by_number = {
            creature.collection_number: creature
            for creature in self._unit_of_work.creatures
            if creature.trainer_id == trainer_id
        }
        return [by_number[number] for number in numbers]

    async def get_candy_inventory(self, trainer_id):
        return CandyInventory(dict(self._unit_of_work.inventory._candies))

    async def delete_creatures(self, trainer_id, creatures):
        released_ids = {creature.id for creature in creatures}
        self._unit_of_work.creatures = [
            creature
            for creature in self._unit_of_work.creatures
            if creature.id not in released_ids
        ]

    async def save_candy_inventory(self, trainer_id, inventory):
        if self._unit_of_work.fail_on_save:
            raise RuntimeError("candy persistence failed")
        self._unit_of_work.inventory = inventory


@pytest.mark.asyncio
async def test_release_application_service_releases_creatures():

    creature = CreatureBuilder().with_collection_number(1).build()

    creature_repository = FakeCreatureRepository(
        creature,
    )

    candy_repository = FakeCandyRepository()

    service = ReleaseApplicationService(
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        reward_policy=RewardPolicy(),
    )

    result = await service.release(
        trainer_id=creature.trainer_id,
        collection_numbers=[1],
    )

    assert result.success

    assert creature in creature_repository.deleted

    inventory = await candy_repository.get(
        creature.trainer_id,
    )

    assert inventory.has(
        result.reward_bundle,
    )


@pytest.mark.asyncio
async def test_release_application_service_releases_multiple_creatures():

    first = CreatureBuilder().with_collection_number(1).build()

    second = CreatureBuilder().with_collection_number(2).build()

    creature_repository = FakeCreatureRepository(
        first,
        second,
    )

    candy_repository = FakeCandyRepository()

    service = ReleaseApplicationService(
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        reward_policy=RewardPolicy(),
    )

    result = await service.release(
        trainer_id=first.trainer_id,
        collection_numbers=[1, 2],
    )

    assert result.success

    assert first in creature_repository.deleted
    assert second in creature_repository.deleted

    assert result.released_creatures == [
        first,
        second,
    ]

    inventory = await candy_repository.get(
        first.trainer_id,
    )

    assert inventory.has(
        result.reward_bundle,
    )


@pytest.mark.asyncio
async def test_release_rejects_repeated_collection_numbers_before_loading():
    creature = CreatureBuilder().with_collection_number(1).build()
    creature_repository = FakeCreatureRepository(creature)
    service = ReleaseApplicationService(
        creature_repository,
        FakeCandyRepository(),
        RewardPolicy(),
    )

    with pytest.raises(ValueError, match="unique"):
        await service.release(creature.trainer_id, [1, 1])

    assert creature_repository.deleted == []


@pytest.mark.asyncio
async def test_release_loads_everything_before_mutating_on_failure():
    first = CreatureBuilder().with_collection_number(1).build()
    second = CreatureBuilder().with_collection_number(2).build()
    creature_repository = FakeCreatureRepository(first, second)
    candy_repository = FakeCandyRepository()
    service = ReleaseApplicationService(
        creature_repository,
        candy_repository,
        _FailingRewardPolicy(),
    )

    with pytest.raises(ValueError, match="reward calculation failed"):
        await service.release(first.trainer_id, [1, 2])

    assert creature_repository.deleted == []
    assert candy_repository.saved == []


@pytest.mark.asyncio
async def test_atomic_release_rolls_back_creatures_when_candy_persistence_fails():
    first = CreatureBuilder().with_collection_number(1).build()
    second = CreatureBuilder().with_collection_number(2).build()
    unit_of_work = _AtomicReleaseUnitOfWork(first, second, fail_on_save=True)
    service = ReleaseApplicationService(
        creature_repository=None,
        candy_repository=None,
        reward_policy=RewardPolicy(),
        unit_of_work=unit_of_work,
    )

    with pytest.raises(RuntimeError, match="candy persistence failed"):
        await service.release(first.trainer_id, [1, 2])

    assert unit_of_work.creatures == [first, second]
    assert unit_of_work.inventory.is_empty()


@pytest.mark.asyncio
async def test_atomic_release_commits_creatures_and_candies_together():
    first = CreatureBuilder().with_collection_number(1).build()
    second = CreatureBuilder().with_collection_number(2).build()
    unit_of_work = _AtomicReleaseUnitOfWork(first, second)
    service = ReleaseApplicationService(
        creature_repository=None,
        candy_repository=None,
        reward_policy=RewardPolicy(),
        unit_of_work=unit_of_work,
    )

    result = await service.release(first.trainer_id, [1, 2])

    assert result.success
    assert unit_of_work.creatures == []
    assert unit_of_work.inventory.has(result.reward_bundle)


@pytest.mark.asyncio
async def test_release_and_preview_share_stage_reward_for_multiple_evolutions():
    stages = [
        SpeciesBuilder()
        .with_id(1)
        .with_evolution_chain(EvolutionChain(1, [1], {}))
        .build(),
        SpeciesBuilder()
        .with_id(2)
        .with_evolution_chain(EvolutionChain(1, [1, 2], {}))
        .build(),
        SpeciesBuilder()
        .with_id(3)
        .with_evolution_chain(EvolutionChain(1, [1, 2, 3], {}))
        .build(),
    ]
    creatures = [
        CreatureBuilder()
        .with_id(index)
        .with_collection_number(index)
        .with_species(species)
        .build()
        for index, species in enumerate(stages, start=1)
    ]
    repository = FakeCreatureRepository(*creatures)
    preview_service = PreviewReleaseApplicationService(
        repository,
        FakeCandyRepository(),
        RewardPolicy(),
    )
    release_service = ReleaseApplicationService(
        repository,
        FakeCandyRepository(),
        RewardPolicy(),
    )

    preview = await preview_service.preview(1, [1, 2, 3])
    released = await release_service.release(1, [1, 2, 3])

    assert dict(preview.reward_bundle.items()) == dict(released.reward_bundle.items())
    assert released.reward_bundle.get(CandyType.FIRE) == 12
