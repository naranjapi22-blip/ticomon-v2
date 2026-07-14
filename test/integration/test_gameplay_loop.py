import uuid

import pytest

from application.bootstrap.core import build_core
from core.capture.domain.capture_ball import CaptureBall
from scripts.create_safari_schema import create_safari_schema


class AlwaysMasterBallSelector:
    """
    Deterministic selector used by integration tests.
    """

    def select(self) -> CaptureBall:
        return CaptureBall.MASTER_BALL


@pytest.mark.asyncio
async def test_complete_gameplay_loop():
    # Arrange
    await create_safari_schema()
    services = build_core(
        ball_selector=AlwaysMasterBallSelector(),
    )

    trainer_id = uuid.uuid4().int & 0x7FFFFFFF
    guild_id = uuid.uuid4().int & 0x7FFFFFFF

    inventory_before = await services.candy_repository.get(
        trainer_id,
    )

    # Act
    session = await services.spawn_application.spawn(
        guild_id=guild_id,
        owner_id=trainer_id,
    )

    assert len(session.opportunities) == 3

    selected = await services.select_opportunity_application.select_opportunity(
        guild_id=guild_id,
        opportunity_index=1,
    )

    result = await services.capture_application.capture(
        trainer_id=trainer_id,
        guild_id=guild_id,
    )

    # Assert
    assert result.success
    assert result.creature is not None
    assert not result.reward.is_empty()

    creature = result.creature

    assert creature.id is not None
    assert creature.trainer_id == trainer_id
    assert creature.species.id == selected.species.id

    persisted = await services.creature_repository.get(
        creature.id,
    )

    assert persisted is not None
    assert persisted.id == creature.id
    assert persisted.trainer_id == trainer_id
    assert persisted.species.id == selected.species.id

    inventory_after = await services.candy_repository.get(
        trainer_id,
    )

    assert not inventory_after.is_empty()

    for candy_type, amount in result.reward.items():
        assert (
            inventory_after.get_amount(candy_type)
            == inventory_before.get_amount(candy_type) + amount
        )

    progress = await services.safari_daily_progress_application.get(guild_id)
    assert progress.daily_capture_count == 1
    assert progress.active_player_count == 1
    assert progress.daily_unlock_count == 0
    assert dict(progress.current_influence.amounts) == {
        type_name: 1 for type_name in selected.species.types
    }
