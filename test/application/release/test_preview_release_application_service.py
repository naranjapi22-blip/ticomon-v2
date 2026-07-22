import pytest

from application.release.exceptions import ReleaseCreatureAssignedToTeam
from application.release.preview_release_application_service import (
    PreviewReleaseApplicationService,
)
from core.candy.reward_policy import RewardPolicy
from test.builders.creature_builder import CreatureBuilder
from test.fakes.fake_candy_repository import FakeCandyRepository
from test.fakes.fake_creature_repository import FakeCreatureRepository
from test.fakes.fake_team_repository import FakeTeamRepository


@pytest.mark.asyncio
async def test_preview_release_application_service_returns_preview():

    creature = CreatureBuilder().with_collection_number(1).build()

    creature_repository = FakeCreatureRepository(
        creature,
    )

    candy_repository = FakeCandyRepository()

    service = PreviewReleaseApplicationService(
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        reward_policy=RewardPolicy(),
    )

    result = await service.preview(
        trainer_id=creature.trainer_id,
        collection_numbers=[1],
    )

    assert result.creatures == [
        creature,
    ]

    assert result.reward_bundle.is_empty() is False

    assert creature_repository.deleted == []

    inventory = await candy_repository.get(
        creature.trainer_id,
    )

    assert inventory.is_empty()


@pytest.mark.asyncio
async def test_preview_release_application_service_returns_multiple_creatures():

    first = CreatureBuilder().with_collection_number(1).build()

    second = CreatureBuilder().with_collection_number(2).build()

    creature_repository = FakeCreatureRepository(
        first,
        second,
    )

    candy_repository = FakeCandyRepository()

    service = PreviewReleaseApplicationService(
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        reward_policy=RewardPolicy(),
    )

    result = await service.preview(
        trainer_id=first.trainer_id,
        collection_numbers=[1, 2],
    )

    assert result.creatures == [
        first,
        second,
    ]

    assert result.reward_bundle.is_empty() is False

    assert creature_repository.deleted == []

    inventory = await candy_repository.get(
        first.trainer_id,
    )

    assert inventory.is_empty()


@pytest.mark.asyncio
async def test_preview_rejects_team_creature_with_one_grouped_lookup():
    creature = CreatureBuilder().with_collection_number(1).build()
    creature_repository = FakeCreatureRepository(creature)
    team_repository = FakeTeamRepository()
    await team_repository.add(creature.trainer_id, 1, creature.id)
    service = PreviewReleaseApplicationService(
        creature_repository=creature_repository,
        candy_repository=FakeCandyRepository(),
        reward_policy=RewardPolicy(),
        team_repository=team_repository,
    )

    with pytest.raises(ReleaseCreatureAssignedToTeam) as error:
        await service.preview(creature.trainer_id, [1])

    assert error.value.collection_numbers == [1]
    assert team_repository.assigned_queries == [(creature.trainer_id, [creature.id])]


@pytest.mark.asyncio
async def test_preview_does_not_block_creature_assigned_to_another_trainer():
    creature = CreatureBuilder().with_collection_number(1).build()
    team_repository = FakeTeamRepository()
    await team_repository.add(2, 1, creature.id)
    service = PreviewReleaseApplicationService(
        creature_repository=FakeCreatureRepository(creature),
        candy_repository=FakeCandyRepository(),
        reward_policy=RewardPolicy(),
        team_repository=team_repository,
    )

    result = await service.preview(creature.trainer_id, [1])

    assert result.creatures == [creature]
    assert team_repository.assigned_queries == [(creature.trainer_id, [creature.id])]


@pytest.mark.asyncio
async def test_preview_checks_a_batch_with_one_team_query():
    first = CreatureBuilder().with_id(101).with_collection_number(1).build()
    second = CreatureBuilder().with_id(102).with_collection_number(2).build()
    team_repository = FakeTeamRepository()
    service = PreviewReleaseApplicationService(
        creature_repository=FakeCreatureRepository(first, second),
        candy_repository=FakeCandyRepository(),
        reward_policy=RewardPolicy(),
        team_repository=team_repository,
    )

    await service.preview(first.trainer_id, [1, 2])

    assert team_repository.assigned_queries == [
        (first.trainer_id, [first.id, second.id])
    ]
