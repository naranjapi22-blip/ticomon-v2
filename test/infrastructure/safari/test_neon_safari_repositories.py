from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from core.safari import (
    SafariMapInfluence,
    SafariUnlock,
    SafariUnlockStatus,
    SafariWorld,
)
from infrastructure.safari.neon_safari_unlock_repository import (
    NeonSafariUnlockRepository,
)
from infrastructure.safari.neon_safari_world_repository import (
    NeonSafariWorldRepository,
)


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _Connection:
    def __init__(self, *, fetchrow_results=None, fetch_results=None) -> None:
        self.fetchrow_results = list(fetchrow_results or [])
        self.fetch_results = list(fetch_results or [])
        self.calls: list[tuple[str, tuple]] = []
        self.transaction_entered = False

    async def fetchrow(self, query, *args):
        self.calls.append((query, args))
        return self.fetchrow_results.pop(0)

    async def fetch(self, query, *args):
        self.calls.append((query, args))
        return self.fetch_results.pop(0)

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
async def test_world_repository_saves_with_upsert_and_reconstructs(monkeypatch):
    world = _world()
    row = _world_row(world)
    connection = _Connection(fetchrow_results=[row])
    _replace_pool(monkeypatch, "neon_safari_world_repository", connection)

    restored = await NeonSafariWorldRepository().save(world)

    query, args = connection.calls[0]
    assert "ON CONFLICT (guild_id) DO UPDATE" in query
    assert args[0] == world.guild_id
    assert dict(restored.current_influence.amounts) == {"water": 3}


@pytest.mark.asyncio
async def test_world_repository_returns_none_when_missing(monkeypatch):
    connection = _Connection(fetchrow_results=[None])
    _replace_pool(monkeypatch, "neon_safari_world_repository", connection)

    assert await NeonSafariWorldRepository().get_by_guild_id(123) is None


@pytest.mark.asyncio
async def test_unlock_repository_lists_available_in_fifo_query(monkeypatch):
    older = _unlock_row(_unlock(1, datetime(2026, 7, 13, 10, tzinfo=UTC)))
    newer = _unlock_row(_unlock(2, datetime(2026, 7, 13, 11, tzinfo=UTC)))
    connection = _Connection(fetch_results=[[older, newer]])
    _replace_pool(monkeypatch, "neon_safari_unlock_repository", connection)

    unlocks = await NeonSafariUnlockRepository().get_available_by_guild_id(123)

    query, _ = connection.calls[0]
    assert "status = 'AVAILABLE'" in query
    assert "ORDER BY unlocked_at, id" in query
    assert [unlock.id for unlock in unlocks] == [1, 2]


@pytest.mark.asyncio
async def test_unlock_repository_consumes_next_with_atomic_skip_locked(monkeypatch):
    consumed_at = datetime(2026, 7, 13, 12, tzinfo=UTC)
    session_id = UUID("11111111-1111-1111-1111-111111111111")
    consumed = _unlock(1, datetime(2026, 7, 13, 10, tzinfo=UTC))
    consumed.consume(consumed_at, session_id)
    connection = _Connection(fetchrow_results=[_unlock_row(consumed)])
    _replace_pool(monkeypatch, "neon_safari_unlock_repository", connection)

    result = await NeonSafariUnlockRepository().consume_next(
        123,
        consumed_at,
        session_id,
    )

    query, args = connection.calls[0]
    assert "FOR UPDATE SKIP LOCKED" in query
    assert "UPDATE safari_unlocks" in query
    assert "RETURNING unlock.*" in query
    assert connection.transaction_entered is True
    assert args == (123, consumed_at, session_id)
    assert result is not None
    assert result.status is SafariUnlockStatus.CONSUMED


@pytest.mark.asyncio
async def test_unlock_repository_returns_none_when_queue_is_empty(monkeypatch):
    connection = _Connection(fetchrow_results=[None])
    _replace_pool(monkeypatch, "neon_safari_unlock_repository", connection)

    result = await NeonSafariUnlockRepository().consume_next(
        123,
        datetime(2026, 7, 13, 12),
        UUID("11111111-1111-1111-1111-111111111111"),
    )

    assert result is None
    _, args = connection.calls[0]
    assert args[1] == datetime(2026, 7, 13, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_unlock_repository_consumes_exact_available_unlock(monkeypatch):
    consumed_at = datetime(2026, 7, 13, 12, tzinfo=UTC)
    session_id = UUID("11111111-1111-1111-1111-111111111111")
    consumed = _unlock(7, datetime(2026, 7, 13, 10, tzinfo=UTC))
    consumed.consume(consumed_at, session_id)
    connection = _Connection(fetchrow_results=[_unlock_row(consumed)])
    _replace_pool(monkeypatch, "neon_safari_unlock_repository", connection)

    result = await NeonSafariUnlockRepository().consume(
        7,
        123,
        consumed_at,
        session_id,
    )

    query, args = connection.calls[0]
    assert "WHERE id = $1" in query
    assert "guild_id = $2" in query
    assert "status = 'AVAILABLE'" in query
    assert "RETURNING *" in query
    assert "SKIP LOCKED" not in query
    assert args == (7, 123, consumed_at, session_id)
    assert result is not None
    assert result.id == 7


@pytest.mark.asyncio
async def test_unlock_repository_exact_consume_returns_none_when_unavailable(
    monkeypatch,
):
    connection = _Connection(fetchrow_results=[None])
    _replace_pool(monkeypatch, "neon_safari_unlock_repository", connection)

    result = await NeonSafariUnlockRepository().consume(
        7,
        123,
        datetime(2026, 7, 13, 12),
        UUID("11111111-1111-1111-1111-111111111111"),
    )

    assert result is None


def _replace_pool(monkeypatch, module_name: str, connection: _Connection) -> None:
    async def fake_get_pool():
        return _Pool(connection)

    monkeypatch.setattr(
        f"infrastructure.safari.{module_name}.get_pool",
        fake_get_pool,
    )


def _world() -> SafariWorld:
    return SafariWorld(
        guild_id=123,
        current_progress=42,
        daily_unlock_count=2,
        current_influence=SafariMapInfluence({"water": 3}),
        last_daily_reset_date=date(2026, 7, 13),
    )


def _world_row(world: SafariWorld) -> dict:
    return {
        "guild_id": world.guild_id,
        "current_progress": world.current_progress,
        "daily_unlock_count": world.daily_unlock_count,
        "current_influence": dict(world.current_influence.amounts),
        "last_daily_reset_date": world.last_daily_reset_date,
    }


def _unlock(unlock_id: int, unlocked_at: datetime, guild_id: int = 123):
    return SafariUnlock(
        id=unlock_id,
        guild_id=guild_id,
        level=1,
        encounter_count=5,
        balls_per_participant=9,
        unlocked_at=unlocked_at,
        cycle_date=unlocked_at.date(),
        map_influence=SafariMapInfluence({"grass": 2}),
    )


def _unlock_row(unlock: SafariUnlock) -> dict:
    return {
        "id": unlock.id,
        "guild_id": unlock.guild_id,
        "level": unlock.level,
        "encounter_count": unlock.encounter_count,
        "balls_per_participant": unlock.balls_per_participant,
        "cycle_date": unlock.cycle_date,
        "map_influence": dict(unlock.map_influence.amounts),
        "status": unlock.status.value,
        "unlocked_at": unlock.unlocked_at,
        "consumed_at": unlock.consumed_at,
        "consumed_session_id": unlock.consumed_session_id,
    }
