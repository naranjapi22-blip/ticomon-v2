import pytest

from application.release.release_application_service import (
    ReleaseApplicationService,
)
from core.candy.reward_policy import RewardPolicy
from test.builders.creature_builder import CreatureBuilder
from test.fakes.fake_candy_repository import FakeCandyRepository
from test.fakes.fake_creature_repository import FakeCreatureRepository


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
