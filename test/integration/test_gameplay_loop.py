import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio

from application.bootstrap.core import build_core
from core.capture.domain.capture_ball import CaptureBall
from infrastructure.db_config import get_pool
from scripts.create_safari_schema import create_safari_schema


@pytest_asyncio.fixture
async def gameplay_data():
    await create_safari_schema()
    trainer_id = uuid.uuid4().int & 0x7FFFFFFF
    guild_id = uuid.uuid4().int & 0x7FFFFFFF

    pool = await get_pool()
    async with pool.acquire() as connection:
        starter_creature_id = await connection.fetchval(
            """
            INSERT INTO creatures (
                trainer_id, original_trainer_id, collection_number,
                species_id, current_form_id, is_shiny, nature, size,
                hp_iv, attack_iv, defense_iv, special_attack_iv,
                special_defense_iv, speed_iv
            )
            VALUES (
                $1, $1, 1, 1, NULL, FALSE, 'hardy', 1.0,
                31, 31, 31, 31, 31, 31
            )
            RETURNING id
            """,
            trainer_id,
        )
        await connection.execute(
            """
            INSERT INTO trainers (trainer_id, starter_creature_id, started_at)
            VALUES ($1, $2, $3)
            """,
            trainer_id,
            starter_creature_id,
            datetime.now(UTC).replace(tzinfo=None),
        )

    yield trainer_id, guild_id

    async with pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM trainer_collection_entries WHERE trainer_id = $1",
            trainer_id,
        )
        await connection.execute(
            "DELETE FROM trainer_achievement_activities WHERE trainer_id = $1",
            trainer_id,
        )
        await connection.execute(
            "DELETE FROM trainer_achievement_unlocks WHERE trainer_id = $1",
            trainer_id,
        )
        await connection.execute(
            "DELETE FROM trainer_candies WHERE trainer_id = $1",
            trainer_id,
        )
        await connection.execute(
            "DELETE FROM trainer_mints WHERE trainer_id = $1",
            trainer_id,
        )
        await connection.execute(
            "DELETE FROM creatures WHERE trainer_id = $1",
            trainer_id,
        )
        await connection.execute(
            "DELETE FROM safari_daily_active_trainers WHERE guild_id = $1",
            guild_id,
        )
        await connection.execute(
            "DELETE FROM safari_daily_worlds WHERE guild_id = $1",
            guild_id,
        )
        await connection.execute(
            "DELETE FROM trainers WHERE trainer_id = $1",
            trainer_id,
        )


class AlwaysMasterBallSelector:
    """
    Deterministic selector used by integration tests.
    """

    def select(self) -> CaptureBall:
        return CaptureBall.MASTER_BALL


@pytest.mark.asyncio
async def test_complete_gameplay_loop(gameplay_data):
    # Arrange
    services = build_core(
        ball_selector=AlwaysMasterBallSelector(),
    )

    trainer_id, guild_id = gameplay_data

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

    expected_reward = result.reward
    for achievement in result.achievements:
        expected_reward = expected_reward.merge(achievement.rewarded_candies)

    for candy_type, amount in expected_reward.items():
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
