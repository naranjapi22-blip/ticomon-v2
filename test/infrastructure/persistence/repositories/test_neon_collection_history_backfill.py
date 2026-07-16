from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.collection.history import CollectionEntrySource
from infrastructure.persistence.repositories.neon_collection_history_repository import (
    NeonCollectionHistoryRepository,
)


class _Acquire:
    def __init__(self, connection) -> None:
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Transaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Connection:
    def __init__(self) -> None:
        self.fetch = AsyncMock(
            return_value=(
                {
                    "trainer_id": 7,
                    "species_id": 137,
                    "current_form_id": None,
                    "species_name": "porygon",
                    "variant_name": None,
                },
                {
                    "trainer_id": 7,
                    "species_id": 479,
                    "current_form_id": 148,
                    "species_name": "rotom",
                    "variant_name": "w",
                },
            )
        )
        self.execute = AsyncMock(return_value="INSERT 0 1")

    def transaction(self):
        return _Transaction()


class _Pool:
    def __init__(self, connection) -> None:
        self._connection = connection

    def acquire(self):
        return _Acquire(self._connection)


@pytest.mark.asyncio
async def test_backfill_ignores_creatures_without_a_valid_trainer(monkeypatch):
    connection = _Connection()

    async def get_pool():
        return _Pool(connection)

    monkeypatch.setattr(
        "infrastructure.persistence.repositories.neon_collection_history_repository.get_pool",
        get_pool,
    )

    inserted = await NeonCollectionHistoryRepository().backfill_existing_creatures()

    assert inserted == 1
    query = connection.fetch.await_args.args[0]
    assert "JOIN trainers t ON t.trainer_id = c.trainer_id" in query
    assert connection.execute.await_count == 1


@pytest.mark.asyncio
async def test_noncanonical_collection_alias_is_not_recorded(monkeypatch):
    async def unexpected_pool():
        raise AssertionError("A noncanonical alias must not reach persistence.")

    monkeypatch.setattr(
        "infrastructure.persistence.repositories.neon_collection_history_repository.get_pool",
        unexpected_pool,
    )
    creature = SimpleNamespace(
        id=1,
        trainer_id=7,
        species=SimpleNamespace(id=479, name="rotom"),
        current_form=SimpleNamespace(id=148, name="w"),
    )

    recorded = await NeonCollectionHistoryRepository().record_creature(
        creature, CollectionEntrySource.TRADE
    )

    assert recorded is False
