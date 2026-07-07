import pytest

from application.bootstrap.core import build_core
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.world import World

MAX_CAPTURE_ATTEMPTS = 10


@pytest.mark.asyncio
async def test_complete_gameplay_loop():
    # Arrange
    services = build_core()

    trainer_id = 999999999

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    profile = SpawnProfile(
        opportunity_count=3,
    )

    # Act
    opportunities = await services.spawn_service.spawn(
        context=context,
        profile=profile,
    )

    assert len(opportunities) == 3

    selected = opportunities[0]

    result = None

    for _ in range(MAX_CAPTURE_ATTEMPTS):
        result = await services.capture_application.capture(
            trainer_id=trainer_id,
            opportunity=selected,
        )

        if result.success:
            break

    # Assert
    assert result is not None
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
