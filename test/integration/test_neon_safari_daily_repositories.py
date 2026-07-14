from datetime import UTC, date, datetime
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio

from core.safari import (
    SafariDailyWorld,
    SafariMapInfluence,
    SafariUnlock,
)
from infrastructure.db_config import get_pool
from infrastructure.safari.neon_safari_daily_active_trainer_repository import (
    NeonSafariDailyActiveTrainerRepository,
)
from infrastructure.safari.neon_safari_daily_world_repository import (
    NeonSafariDailyWorldRepository,
)
from infrastructure.safari.neon_safari_unlock_repository import (
    NeonSafariUnlockRepository,
)
from scripts.create_safari_schema import create_safari_schema


@pytest_asyncio.fixture
async def safari_daily_guild_id():
    await create_safari_schema()
    guild_id = uuid4().int & 0x7FFFFFFFFFFFFFFF
    yield guild_id

    pool = await get_pool()
    async with pool.acquire() as connection:
        await connection.execute(
            "DELETE FROM safari_daily_active_trainers WHERE guild_id = $1",
            guild_id,
        )
        await connection.execute(
            "DELETE FROM safari_daily_worlds WHERE guild_id = $1",
            guild_id,
        )
        await connection.execute(
            "DELETE FROM safari_unlocks WHERE guild_id = $1",
            guild_id,
        )


@pytest.mark.asyncio
async def test_daily_world_round_trip_and_lock(safari_daily_guild_id):
    repository = NeonSafariDailyWorldRepository()
    world = SafariDailyWorld(
        guild_id=safari_daily_guild_id,
        cycle_date=date(2026, 7, 14),
        daily_capture_count=12,
        daily_unlock_count=2,
        current_influence=SafariMapInfluence({"water": 5}),
    )

    assert await repository.get(safari_daily_guild_id, date(2026, 7, 14)) is None

    await repository.save(world)
    restored = await repository.get(safari_daily_guild_id, date(2026, 7, 14))

    assert restored == world
    locked = await repository.get_for_update(safari_daily_guild_id, date(2026, 7, 14))
    assert locked == world


@pytest.mark.asyncio
async def test_daily_active_trainer_registration_and_count(safari_daily_guild_id):
    repository = NeonSafariDailyActiveTrainerRepository()
    cycle_date = date(2026, 7, 14)
    first_time = datetime(2026, 7, 14, 12, tzinfo=UTC)

    assert await repository.register_if_absent(
        safari_daily_guild_id,
        cycle_date,
        111,
        first_time,
    )
    assert not await repository.register_if_absent(
        safari_daily_guild_id,
        cycle_date,
        111,
        first_time,
    )
    assert await repository.register_if_absent(
        safari_daily_guild_id,
        cycle_date,
        222,
        first_time,
    )
    assert await repository.count_active(safari_daily_guild_id, cycle_date) == 2


@pytest.mark.asyncio
async def test_unlock_cycle_date_persistence_and_expiry(safari_daily_guild_id):
    repository = NeonSafariUnlockRepository()
    cycle_date = date(2026, 7, 14)
    previous_day = date(2026, 7, 13)

    previous = await repository.save(
        _unlock(
            safari_daily_guild_id,
            previous_day,
            level=1,
        )
    )
    current = await repository.save(
        _unlock(
            safari_daily_guild_id,
            cycle_date,
            level=2,
        )
    )

    assert previous.cycle_date == previous_day
    assert current.cycle_date == cycle_date

    available = await repository.get_available_by_guild_id(
        safari_daily_guild_id,
        cycle_date,
    )
    assert [unlock.id for unlock in available] == [current.id]

    expired = await repository.expire_available_before(
        safari_daily_guild_id,
        cycle_date,
    )
    assert expired == 1

    rows = await _fetch_unlock_rows(safari_daily_guild_id)
    assert {row["status"] for row in rows} == {"EXPIRED", "AVAILABLE"}

    with pytest.raises(asyncpg.UniqueViolationError):
        await repository.save(
            _unlock(
                safari_daily_guild_id,
                cycle_date,
                level=2,
            )
        )


def _unlock(guild_id: int, cycle_date: date, *, level: int) -> SafariUnlock:
    return SafariUnlock(
        id=None,
        guild_id=guild_id,
        level=level,
        encounter_count=7,
        balls_per_participant=12,
        unlocked_at=datetime(2026, 7, 14, 12, tzinfo=UTC),
        cycle_date=cycle_date,
        map_influence=SafariMapInfluence({"grass": 4}),
    )


async def _fetch_unlock_rows(guild_id: int):
    pool = await get_pool()
    async with pool.acquire() as connection:
        return await connection.fetch(
            """
            SELECT status
            FROM safari_unlocks
            WHERE guild_id = $1
            ORDER BY cycle_date, level
            """,
            guild_id,
        )
