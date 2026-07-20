from __future__ import annotations

from types import SimpleNamespace

import pytest

import scripts.sync_creature_loadout_catalog as synchronizer


class FakeTransaction:
    def __init__(self, connection) -> None:
        self.connection = connection

    async def __aenter__(self):
        self.connection.committed_transactions += 1
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self) -> None:
        self.calls = []
        self.committed_transactions = 0

    def transaction(self):
        return FakeTransaction(self)

    async def executemany(self, query, rows):
        self.calls.append((query, list(rows)))


class FakeAcquire:
    def __init__(self, connection) -> None:
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakePool:
    def __init__(self, connection) -> None:
        self.connection = connection

    def acquire(self):
        return FakeAcquire(self.connection)


@pytest.mark.asyncio
async def test_sync_catalog_deduplicates_and_commits_bulk_batches(monkeypatch):
    species = [SimpleNamespace(id=658), SimpleNamespace(id=2)]
    ability = SimpleNamespace(
        id="static", display_name="Static", slot=1, is_hidden=False
    )
    hidden_ability = SimpleNamespace(
        id="lightningrod", display_name="Lightning Rod", slot=3, is_hidden=True
    )
    duplicate_slot_ability = SimpleNamespace(
        id="overgrow", display_name="Overgrow", slot=3, is_hidden=False
    )
    move = SimpleNamespace(
        id="tackle",
        display_name="Tackle",
        move_type="normal",
        category="physical",
        base_power=40,
        accuracy=100,
        pp=35,
        priority=0,
    )
    second_move = SimpleNamespace(
        id="thunderbolt",
        display_name="Thunderbolt",
        move_type="electric",
        category="special",
        base_power=90,
        accuracy=100,
        pp=15,
        priority=0,
    )

    class FakeCatalog:
        def abilities_for(self, item):
            return (
                (ability, hidden_ability, duplicate_slot_ability)
                if item.id == 658
                else (ability,)
            )

        def moves_for(self, item):
            return (move, second_move, move) if item.id == 658 else (move,)

    connection = FakeConnection()
    monkeypatch.setattr(synchronizer, "get_pool", lambda: _pool(connection))
    monkeypatch.setattr(synchronizer, "close_pool", _close_pool)
    monkeypatch.setattr(
        synchronizer, "NeonSpeciesRepository", lambda: _repository(species)
    )
    monkeypatch.setattr(synchronizer, "PokeEnvLoadoutCatalog", FakeCatalog)
    monkeypatch.setattr(synchronizer, "RELATIONSHIP_BATCH_SIZE", 1)

    summary = await synchronizer.sync_catalog()

    assert summary["species"] == 2
    assert summary["abilities"] == 4
    assert summary["moves"] == 4
    assert summary["rows_written"] == 2 + 2 + 3 + 3
    assert connection.committed_transactions == 8
    assert [query for query, _ in connection.calls] == [
        synchronizer.ABILITY_INSERT,
        synchronizer.MOVE_INSERT,
        synchronizer.SPECIES_ABILITY_INSERT,
        synchronizer.SPECIES_ABILITY_INSERT,
        synchronizer.SPECIES_ABILITY_INSERT,
        synchronizer.SPECIES_MOVE_INSERT,
        synchronizer.SPECIES_MOVE_INSERT,
        synchronizer.SPECIES_MOVE_INSERT,
    ]
    assert all("ON CONFLICT" in query for query, _ in connection.calls)
    species_ability_rows = [
        rows
        for query, rows in connection.calls
        if query == synchronizer.SPECIES_ABILITY_INSERT
    ]
    flattened_ability_rows = [row for batch in species_ability_rows for row in batch]
    assert {(row[0], row[2]) for row in flattened_ability_rows} == {
        (658, 1),
        (658, 3),
        (2, 1),
    }
    assert (658, "lightningrod", 3, True) in flattened_ability_rows
    assert (658, "overgrow", 3, False) not in flattened_ability_rows


@pytest.mark.asyncio
async def test_dry_run_does_not_write_batches(monkeypatch):
    species = [SimpleNamespace(id=1)]

    class FakeCatalog:
        def abilities_for(self, item):
            return ()

        def moves_for(self, item):
            return ()

    connection = FakeConnection()
    monkeypatch.setattr(synchronizer, "get_pool", lambda: _pool(connection))
    monkeypatch.setattr(synchronizer, "close_pool", _close_pool)
    monkeypatch.setattr(
        synchronizer, "NeonSpeciesRepository", lambda: _repository(species)
    )
    monkeypatch.setattr(synchronizer, "PokeEnvLoadoutCatalog", FakeCatalog)

    summary = await synchronizer.sync_catalog(dry_run=True)

    assert summary["species"] == 1
    assert summary["rows_written"] == 0
    assert connection.calls == []
    assert connection.committed_transactions == 0


async def _pool(connection):
    return FakePool(connection)


async def _close_pool():
    return None


def _repository(species):
    class Repository:
        async def get_all(self):
            return species

    return Repository()
