import pytest

from application.bootstrap.core import build_core
from core.capture.domain.capture_ball import CaptureBall


class AlwaysMasterBallSelector:
    """
    Deterministic selector used by integration tests.
    """

    def select(self) -> CaptureBall:
        return CaptureBall.MASTER_BALL


@pytest.mark.asyncio
async def test_complete_gameplay_loop():
    # Arrange
    services = build_core(
        ball_selector=AlwaysMasterBallSelector(),
    )

    trainer_id = 999999999

    # Act
    session = await services.spawn_application.spawn()

    assert len(session.opportunities) == 3

    selected = await services.select_opportunity_application.select_opportunity(
        opportunity_index=1,
    )

    result = await services.capture_application.capture(
        trainer_id=trainer_id,
    )

    # Assert
    assert result.success
    assert result.creature is not None

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
