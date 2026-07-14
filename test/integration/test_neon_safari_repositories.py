import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import asyncpg
import pytest
import pytest_asyncio

from core.safari import (
    SafariMapInfluence,
    SafariUnlock,
    SafariUnlockStatus,
    SafariWorld,
)
from infrastructure.db_config import get_pool
from infrastructure.safari.neon_safari_unlock_repository import (
    NeonSafariUnlockRepository,
)
from infrastructure.safari.neon_safari_world_repository import (
    NeonSafariWorldRepository,
)
from scripts.create_safari_schema import create_safari_schema


@pytest_asyncio.fixture
async def safari_guild_id():
    await create_safari_schema()
    guild_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
    yield guild_id

    pool = await get_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM safari_unlocks WHERE guild_id = $1",
            guild_id,
        )
        await connection.execute(
            "DELETE FROM safari_worlds WHERE guild_id = $1",
            guild_id,
        )


@pytest.mark.asyncio
async def test_world_round_trip_and_update(safari_guild_id):
    repository = NeonSafariWorldRepository()
    world = SafariWorld(
        guild_id=safari_guild_id,
        current_progress=12,
        daily_unlock_count=1,
        current_influence=SafariMapInfluence(),
        last_daily_reset_date=date(2026, 7, 13),
    )

    assert await repository.get_by_guild_id(safari_guild_id) is None

    saved = await repository.save(world)
    assert saved.current_progress == 12
    assert saved.current_influence.is_empty()

    world.current_progress = 87
    world.daily_unlock_count = 3
    world.current_influence = SafariMapInfluence({"water": 5, "flying": 2})
    await repository.save(world)
    restored = await repository.get_by_guild_id(safari_guild_id)

    assert restored is not None
    assert restored.current_progress == 87
    assert restored.daily_unlock_count == 3
    assert dict(restored.current_influence.amounts) == {
        "water": 5,
        "flying": 2,
    }


@pytest.mark.asyncio
async def test_unlock_fifo_consumption_and_guild_isolation(safari_guild_id):
    repository = NeonSafariUnlockRepository()
    other_guild_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
    now = datetime.now(UTC)

    later = await repository.save(
        _unlock(safari_guild_id, now + timedelta(seconds=1), level=2)
    )
    oldest = await repository.save(_unlock(safari_guild_id, now, level=1))
    other = await repository.save(
        _unlock(other_guild_id, now - timedelta(days=1), level=1)
    )

    available = await repository.get_available_by_guild_id(safari_guild_id)
    assert [unlock.id for unlock in available] == [oldest.id, later.id]

    consumed = await repository.consume_next(
        safari_guild_id,
        now + timedelta(minutes=1),
        uuid.uuid4(),
    )
    assert consumed is not None
    assert consumed.id == oldest.id
    assert consumed.status is SafariUnlockStatus.CONSUMED
    assert [
        unlock.id
        for unlock in await repository.get_available_by_guild_id(safari_guild_id)
    ] == [later.id]
    assert [
        unlock.id
        for unlock in await repository.get_available_by_guild_id(other_guild_id)
    ] == [other.id]

    pool = await get_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM safari_unlocks WHERE guild_id = $1",
            other_guild_id,
        )


@pytest.mark.asyncio
async def test_concurrent_consumers_do_not_receive_same_unlock(safari_guild_id):
    repository = NeonSafariUnlockRepository()
    now = datetime.now(UTC)
    saved = await repository.save(_unlock(safari_guild_id, now, level=1))

    results = await asyncio.gather(
        repository.consume_next(safari_guild_id, now, uuid.uuid4()),
        repository.consume_next(safari_guild_id, now, uuid.uuid4()),
    )

    consumed = [result for result in results if result is not None]
    assert len(consumed) == 1
    assert consumed[0].id == saved.id
    assert (
        await repository.consume_next(
            safari_guild_id,
            now,
            uuid.uuid4(),
        )
        is None
    )


@pytest.mark.asyncio
async def test_exact_unlock_consumption_is_atomic_and_preserves_fifo_api(
    safari_guild_id,
):
    repository = NeonSafariUnlockRepository()
    now = datetime.now(UTC)
    first = await repository.save(_unlock(safari_guild_id, now, level=2))
    second = await repository.save(
        _unlock(safari_guild_id, now + timedelta(seconds=1), level=3)
    )

    results = await asyncio.gather(
        repository.consume(second.id, safari_guild_id, now, uuid.uuid4()),
        repository.consume(second.id, safari_guild_id, now, uuid.uuid4()),
    )

    assert sum(result is not None for result in results) == 1
    assert all(result is None or result.id == second.id for result in results)
    assert (
        await repository.consume(
            second.id,
            safari_guild_id,
            now,
            uuid.uuid4(),
        )
        is None
    )

    consumed_next = await repository.consume_next(
        safari_guild_id,
        now,
        uuid.uuid4(),
    )
    assert consumed_next is not None
    assert consumed_next.id == first.id


@pytest.mark.asyncio
async def test_exact_unlock_consume_rejects_another_guild(safari_guild_id):
    repository = NeonSafariUnlockRepository()
    now = datetime.now(UTC)
    saved = await repository.save(_unlock(safari_guild_id, now, level=1))

    assert (
        await repository.consume(
            saved.id,
            safari_guild_id + 1,
            now,
            uuid.uuid4(),
        )
        is None
    )
    assert [
        unlock.id
        for unlock in await repository.get_available_by_guild_id(safari_guild_id)
    ] == [saved.id]


@pytest.mark.asyncio
async def test_database_constraints_reject_invalid_world(safari_guild_id):
    pool = await get_pool()

    async with pool.acquire() as connection:
        with pytest.raises(asyncpg.CheckViolationError):
            await connection.execute(
                """
                INSERT INTO safari_worlds (
                    guild_id,
                    current_progress,
                    daily_unlock_count,
                    current_influence,
                    last_daily_reset_date
                )
                VALUES ($1, -1, 0, '{}'::jsonb, $2)
                """,
                safari_guild_id,
                date(2026, 7, 13),
            )


def _unlock(
    guild_id: int,
    unlocked_at: datetime,
    *,
    level: int,
) -> SafariUnlock:
    return SafariUnlock(
        id=None,
        guild_id=guild_id,
        level=level,
        encounter_count=7,
        balls_per_participant=12,
        unlocked_at=unlocked_at,
        cycle_date=unlocked_at.date(),
        map_influence=SafariMapInfluence({"grass": 4}),
    )
