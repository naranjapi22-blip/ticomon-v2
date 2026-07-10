import pytest

from application.release.preview_release_application_service import (
    PreviewReleaseApplicationService,
)
from core.candy.reward_policy import RewardPolicy
from test.builders.creature_builder import CreatureBuilder
from test.fakes.fake_candy_repository import FakeCandyRepository
from test.fakes.fake_creature_repository import FakeCreatureRepository


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
