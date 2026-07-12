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
