from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from core.safari import (
    SafariDailyWorld,
    SafariMapInfluence,
    SafariUnlock,
    SafariUnlockStatus,
)
from infrastructure.safari.neon_safari_daily_active_trainer_repository import (
    NeonSafariDailyActiveTrainerRepository,
)
from infrastructure.safari.neon_safari_daily_world_repository import (
    NeonSafariDailyWorldRepository,
)
from infrastructure.safari.neon_safari_unlock_repository import (
    NeonSafariUnlockRepository,
)


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _Connection:
    def __init__(
        self,
        *,
        fetchrow_results=None,
        fetch_results=None,
        fetchval_results=None,
        execute_results=None,
    ) -> None:
        self.fetchrow_results = list(fetchrow_results or [])
        self.fetch_results = list(fetch_results or [])
        self.fetchval_results = list(fetchval_results or [])
        self.execute_results = list(execute_results or [])
        self.calls: list[tuple[str, tuple]] = []
        self.transaction_entered = False

    async def fetchrow(self, query, *args):
        self.calls.append((query, args))
        return self.fetchrow_results.pop(0) if self.fetchrow_results else None

    async def fetch(self, query, *args):
        self.calls.append((query, args))
        return self.fetch_results.pop(0) if self.fetch_results else []

    async def fetchval(self, query, *args):
        self.calls.append((query, args))
        return self.fetchval_results.pop(0) if self.fetchval_results else 0

    async def execute(self, query, *args):
        self.calls.append((query, args))
        return self.execute_results.pop(0) if self.execute_results else "UPDATE 0"

    def transaction(self):
        self.transaction_entered = True
        return _Transaction()


class _Acquire:
    def __init__(self, connection) -> None:
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _Pool:
    def __init__(self, connection) -> None:
        self.connection = connection

    def acquire(self):
        return _Acquire(self.connection)


@pytest.mark.asyncio
async def test_daily_world_repository_get_or_create_and_save(monkeypatch):
    world = SafariDailyWorld(
        guild_id=123,
        cycle_date=date(2026, 7, 14),
        daily_capture_count=4,
        daily_unlock_count=2,
        current_influence=SafariMapInfluence({"grass": 3}),
    )
    connection = _Connection(fetchrow_results=[_world_row(world), _world_row(world)])
    _replace_pool(monkeypatch, "neon_safari_daily_world_repository", connection)

    repository = NeonSafariDailyWorldRepository()
    restored = await repository.get_or_create(123, date(2026, 7, 14))

    assert restored == world
    query, args = connection.calls[0]
    assert "INSERT INTO safari_daily_worlds" in query
    assert args[1] == date(2026, 7, 14)

    await repository.save(world)
    assert any(
        "ON CONFLICT (guild_id, cycle_date) DO UPDATE" in call[0]
        for call in connection.calls
    )


@pytest.mark.asyncio
async def test_daily_world_repository_get_for_update_and_get(monkeypatch):
    world = SafariDailyWorld(
        guild_id=123,
        cycle_date=date(2026, 7, 14),
        daily_capture_count=9,
        daily_unlock_count=3,
        current_influence=SafariMapInfluence({"water": 2}),
    )
    connection = _Connection(fetchrow_results=[_world_row(world), _world_row(world)])
    _replace_pool(monkeypatch, "neon_safari_daily_world_repository", connection)

    repository = NeonSafariDailyWorldRepository()
    locked = await repository.get_for_update(123, date(2026, 7, 14))
    plain = await repository.get(123, date(2026, 7, 14))

    assert locked == world
    assert plain == world
    assert "FOR UPDATE" in connection.calls[0][0]


@pytest.mark.asyncio
async def test_daily_active_trainer_repository_registers_once_and_counts(monkeypatch):
    connection = _Connection(
        fetchrow_results=[{"trainer_id": 7}, None],
        fetchval_results=[2],
    )
    _replace_pool(
        monkeypatch,
        "neon_safari_daily_active_trainer_repository",
        connection,
    )

    repository = NeonSafariDailyActiveTrainerRepository()
    inserted = await repository.register_if_absent(
        123,
        date(2026, 7, 14),
        7,
        datetime(2026, 7, 14, 12, tzinfo=UTC),
    )
    duplicate = await repository.register_if_absent(
        123,
        date(2026, 7, 14),
        7,
        datetime(2026, 7, 14, 12, tzinfo=UTC),
    )
    count = await repository.count_active(123, date(2026, 7, 14))

    assert inserted is True
    assert duplicate is False
    assert count == 2
    assert (
        "ON CONFLICT (guild_id, cycle_date, trainer_id) DO NOTHING"
        in connection.calls[0][0]
    )
    assert "SELECT COUNT(*)" in connection.calls[-1][0]


@pytest.mark.asyncio
async def test_unlock_repository_filters_cycle_and_expires_previous(monkeypatch):
    connection = _Connection(
        fetch_results=[[_unlock_row(_unlock(1, date(2026, 7, 14)))]],
        fetchrow_results=[_unlock_row(_unlock(1, date(2026, 7, 14)))],
        execute_results=["UPDATE 3"],
    )
    _replace_pool(monkeypatch, "neon_safari_unlock_repository", connection)

    repository = NeonSafariUnlockRepository()
    unlocks = await repository.get_available_by_guild_id(123, date(2026, 7, 14))
    expired = await repository.expire_available_before(123, date(2026, 7, 14))

    assert len(unlocks) == 1
    assert expired == 3
    assert "cycle_date = $2" in connection.calls[0][0]
    assert "status = 'EXPIRED'" in connection.calls[1][0]


@pytest.mark.asyncio
async def test_unlock_repository_consume_next_can_filter_cycle(monkeypatch):
    connection = _Connection(
        fetchrow_results=[
            _unlock_row(
                _unlock(
                    1,
                    date(2026, 7, 14),
                    status=SafariUnlockStatus.CONSUMED,
                    consumed_at=datetime(2026, 7, 14, 13, tzinfo=UTC),
                    consumed_session_id=UUID("11111111-1111-1111-1111-111111111111"),
                )
            )
        ],
    )
    _replace_pool(monkeypatch, "neon_safari_unlock_repository", connection)

    repository = NeonSafariUnlockRepository()
    result = await repository.consume_next(
        123,
        datetime(2026, 7, 14, 12, tzinfo=UTC),
        UUID("11111111-1111-1111-1111-111111111111"),
        date(2026, 7, 14),
    )

    assert result is not None
    assert "cycle_date = $4" in connection.calls[0][0]


def _replace_pool(monkeypatch, module_name: str, connection: _Connection) -> None:
    async def fake_get_pool():
        return _Pool(connection)

    monkeypatch.setattr(
        f"infrastructure.safari.{module_name}.get_pool",
        fake_get_pool,
    )


def _world_row(world: SafariDailyWorld) -> dict:
    return {
        "guild_id": world.guild_id,
        "cycle_date": world.cycle_date,
        "daily_capture_count": world.daily_capture_count,
        "daily_unlock_count": world.daily_unlock_count,
        "current_influence": dict(world.current_influence.amounts),
    }


def _unlock(
    unlock_id: int,
    cycle_date: date,
    *,
    status: SafariUnlockStatus = SafariUnlockStatus.AVAILABLE,
    consumed_at: datetime | None = None,
    consumed_session_id: UUID | None = None,
) -> SafariUnlock:
    return SafariUnlock(
        id=unlock_id,
        guild_id=123,
        level=1,
        encounter_count=5,
        balls_per_participant=9,
        unlocked_at=datetime(2026, 7, 14, 12, tzinfo=UTC),
        cycle_date=cycle_date,
        map_influence=SafariMapInfluence({"grass": 2}),
        status=status,
        consumed_at=consumed_at,
        consumed_session_id=consumed_session_id,
    )


def _unlock_row(unlock: SafariUnlock) -> dict:
    values = NeonSafariUnlockRepository()._mapper.to_row(unlock)
    return {
        "id": unlock.id,
        "guild_id": values[0],
        "level": values[1],
        "encounter_count": values[2],
        "balls_per_participant": values[3],
        "cycle_date": values[4],
        "map_influence": values[5],
        "status": values[6],
        "unlocked_at": values[7],
        "consumed_at": values[8],
        "consumed_session_id": values[9],
    }
