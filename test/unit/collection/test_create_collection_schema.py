import pytest

import scripts.create_collection_schema as schema_module


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _Connection:
    def __init__(self):
        self.calls = []

    async def execute(self, query):
        self.calls.append(query)

    def transaction(self):
        return _Transaction()


class _Acquire:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _Pool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return _Acquire(self.connection)


@pytest.mark.asyncio
async def test_schema_creates_historical_entries_and_idempotent_claims(monkeypatch):
    connection = _Connection()

    async def get_pool():
        return _Pool(connection)

    async def close_pool():
        return None

    monkeypatch.setattr(schema_module, "get_pool", get_pool)
    monkeypatch.setattr(schema_module, "close_pool", close_pool)
    await schema_module.create_collection_schema()

    statements = "\n".join(connection.calls)
    assert "CREATE TABLE IF NOT EXISTS trainer_collection_entries" in statements
    assert "trainer_id BIGINT" in statements
    assert "variant_id BIGINT NULL" in statements
    assert "COALESCE(variant_id, 0)" in statements
    assert "CREATE TABLE IF NOT EXISTS trainer_collection_claims" in statements
    assert "PRIMARY KEY (trainer_id, collection_id, milestone)" in statements
