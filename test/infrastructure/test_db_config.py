from unittest.mock import AsyncMock

import pytest

import infrastructure.db_config as db_config


@pytest.mark.asyncio
async def test_get_pool_disables_statement_cache(monkeypatch):
    db_config._pool = None
    pool = AsyncMock()
    create_pool = AsyncMock(return_value=pool)
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://example.test/db")
    monkeypatch.setattr(db_config.asyncpg, "create_pool", create_pool)

    try:
        await db_config.get_pool()

        create_pool.assert_awaited_once_with(
            dsn="postgresql://example.test/db",
            min_size=1,
            max_size=10,
            statement_cache_size=0,
        )
    finally:
        await db_config.close_pool()


@pytest.mark.asyncio
async def test_get_pool_recreates_pool_when_event_loop_changes(monkeypatch):
    first_pool = AsyncMock()
    second_pool = AsyncMock()
    create_pool = AsyncMock(side_effect=[first_pool, second_pool])
    monkeypatch.setenv("NEON_DATABASE_URL", "postgresql://example.test/db")
    monkeypatch.setattr(db_config.asyncpg, "create_pool", create_pool)

    first_loop = object()
    second_loop = object()
    loops = iter((first_loop, second_loop))
    monkeypatch.setattr(db_config.asyncio, "get_running_loop", lambda: next(loops))

    await db_config.get_pool()
    db_config._pool_loop = first_loop
    pool = await db_config.get_pool()

    assert pool is second_pool
    first_pool.terminate.assert_called_once_with()
    assert create_pool.await_count == 2
    db_config._pool = None
    db_config._pool_loop = None
