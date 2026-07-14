from __future__ import annotations

from datetime import date

import pytest

import scripts.create_safari_schema as create_safari_schema_module


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _Connection:
    def __init__(self, *, duplicate_row=None) -> None:
        self.duplicate_row = duplicate_row
        self.calls: list[tuple[str, tuple]] = []

    async def execute(self, query, *args):
        self.calls.append((query, args))
        return "OK"

    async def fetchrow(self, query, *args):
        self.calls.append((query, args))
        return self.duplicate_row

    def transaction(self):
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
async def test_create_safari_schema_emits_daily_tables_and_unlock_audit_in_order(
    monkeypatch,
):
    connection = _Connection()
    _replace_pool(monkeypatch, connection)

    ensure_calls = []

    async def fake_ensure_creature_original_trainer_id(_connection):
        ensure_calls.append(True)

    monkeypatch.setattr(
        create_safari_schema_module,
        "ensure_creature_original_trainer_id",
        fake_ensure_creature_original_trainer_id,
    )

    await create_safari_schema_module.create_safari_schema()

    queries = [query for query, _ in connection.calls]
    assert any(
        "CREATE TABLE IF NOT EXISTS safari_daily_worlds" in query for query in queries
    )
    assert any(
        "CREATE TABLE IF NOT EXISTS safari_daily_active_trainers" in query
        for query in queries
    )
    assert any(
        "SELECT guild_id, cycle_date, level, COUNT(*) AS count" in query
        for query in queries
    )
    assert any(
        "CREATE UNIQUE INDEX IF NOT EXISTS safari_unlocks_unique_cycle_level_idx"
        in query
        for query in queries
    )
    assert any("DROP TABLE IF EXISTS safari_worlds" in query for query in queries)
    assert ensure_calls == [True]
    assert queries.index(
        next(
            query
            for query in queries
            if "SELECT guild_id, cycle_date, level, COUNT(*) AS count" in query
        )
    ) < queries.index(
        next(
            query
            for query in queries
            if "CREATE UNIQUE INDEX IF NOT EXISTS safari_unlocks_unique_cycle_level_idx"
            in query
        )
    )


@pytest.mark.asyncio
async def test_create_safari_schema_fails_before_unique_index_when_duplicates_exist(
    monkeypatch,
):
    duplicate_row = {
        "guild_id": 123,
        "cycle_date": date(2026, 7, 14),
        "level": 1,
        "count": 2,
    }
    connection = _Connection(duplicate_row=duplicate_row)
    _replace_pool(monkeypatch, connection)

    async def fake_ensure_creature_original_trainer_id(_connection):
        return None

    monkeypatch.setattr(
        create_safari_schema_module,
        "ensure_creature_original_trainer_id",
        fake_ensure_creature_original_trainer_id,
    )

    with pytest.raises(RuntimeError, match="Duplicate safari_unlocks rows exist"):
        await create_safari_schema_module.create_safari_schema()

    assert all(
        "CREATE UNIQUE INDEX IF NOT EXISTS safari_unlocks_unique_cycle_level_idx"
        not in query
        for query, _ in connection.calls
    )


def _replace_pool(monkeypatch, connection: _Connection) -> None:
    async def fake_get_pool():
        return _Pool(connection)

    monkeypatch.setattr(create_safari_schema_module, "get_pool", fake_get_pool)
