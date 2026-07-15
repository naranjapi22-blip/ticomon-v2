from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from core.species.species_repository import SpeciesRepository
from infrastructure.persistence.repositories.neon_creature_repository import (
    NeonCreatureRepository,
)
from test.builders.creature_builder import CreatureBuilder
from test.builders.species_builder import SpeciesBuilder


class _FakeConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.events: list[str] = []

    def transaction(self) -> _FakeTransaction:
        return _FakeTransaction(self)

    async def fetch(self, query: str, trainer_id: int) -> list[dict]:
        return self.rows


class _FakeTransaction:
    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _FakeConnection:
        self.connection.events.append("transaction_enter")
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.connection.events.append("transaction_exit")
        return None


class _FakeAcquire:
    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _FakeConnection:
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakePool:
    def __init__(self, connection: _FakeConnection) -> None:
        self.connection = connection

    def acquire(self) -> _FakeAcquire:
        return _FakeAcquire(self.connection)


class _SaveFakeConnection(_FakeConnection):
    def __init__(self, row: dict) -> None:
        super().__init__([])
        self.row = row

    async def execute(self, query: str, trainer_id: int) -> None:
        assert "pg_advisory_xact_lock" in query
        self.events.append("lock")

    async def fetchval(self, query: str, trainer_id: int) -> int:
        assert "MAX(collection_number)" in query
        self.events.append("max")
        return 4

    async def fetchrow(self, query: str, *args):
        if "INSERT INTO creatures" in query:
            self.events.append("insert")
            return {"id": self.row["id"]}
        self.events.append("reload")
        return self.row


@pytest.mark.asyncio
async def test_get_by_trainer_loads_species_in_one_batch(monkeypatch) -> None:
    fire = SpeciesBuilder().with_id(1).with_name("Charmander").build()
    water = (
        SpeciesBuilder()
        .with_id(2)
        .with_name("Squirtle")
        .with_types(
            ["water"],
        )
        .build()
    )

    species_repository = AsyncMock(spec=SpeciesRepository)
    species_repository.get_many = AsyncMock(return_value=[fire, water])
    species_repository.get = AsyncMock()

    rows = [
        {
            "id": 10,
            "collection_number": 7,
            "species_id": 1,
            "trainer_id": 99,
            "hp_iv": 31,
            "attack_iv": 30,
            "defense_iv": 29,
            "special_attack_iv": 28,
            "special_defense_iv": 27,
            "speed_iv": 26,
            "size": 1.5,
            "nature": "hardy",
            "is_shiny": True,
            "variant_id": 40,
            "variant_name": "Mega",
            "current_form_id": 40,
        },
        {
            "id": 11,
            "collection_number": 8,
            "species_id": 2,
            "trainer_id": 99,
            "hp_iv": 21,
            "attack_iv": 20,
            "defense_iv": 19,
            "special_attack_iv": 18,
            "special_defense_iv": 17,
            "speed_iv": 16,
            "size": 1.0,
            "nature": "modest",
            "is_shiny": False,
            "variant_id": None,
            "variant_name": None,
            "current_form_id": None,
        },
        {
            "id": 12,
            "collection_number": 9,
            "species_id": 1,
            "trainer_id": 99,
            "hp_iv": 11,
            "attack_iv": 10,
            "defense_iv": 9,
            "special_attack_iv": 8,
            "special_defense_iv": 7,
            "speed_iv": 6,
            "size": 1.25,
            "nature": "bold",
            "is_shiny": False,
            "variant_id": None,
            "variant_name": None,
            "current_form_id": None,
        },
    ]

    fake_pool = _FakePool(_FakeConnection(rows))

    async def fake_get_pool():
        return fake_pool

    monkeypatch.setattr(
        "infrastructure.persistence.repositories.neon_creature_repository.get_pool",
        fake_get_pool,
    )

    repository = NeonCreatureRepository(
        species_repository=species_repository,
    )

    creatures = await repository.get_by_trainer(trainer_id=99)

    species_repository.get_many.assert_awaited_once_with([1, 2])
    species_repository.get.assert_not_called()

    assert [creature.id for creature in creatures] == [10, 11, 12]
    assert creatures[0].species == fire
    assert creatures[0].current_form is not None
    assert creatures[0].current_form.id == 40
    assert creatures[0].current_form.name == "Mega"
    assert creatures[0].original_trainer_id == 99
    assert creatures[0].collection_number == 7
    assert creatures[0].ivs.hp == 31
    assert creatures[0].is_shiny is True
    assert creatures[0].nature.name == "hardy"
    assert creatures[0].size.value == 1.5
    assert creatures[1].species == water
    assert creatures[1].current_form is None
    assert creatures[1].original_trainer_id == 99
    assert creatures[1].collection_number == 8
    assert creatures[1].ivs.attack == 20
    assert creatures[1].is_shiny is False
    assert creatures[1].nature.name == "modest"
    assert creatures[1].size.value == 1.0


@pytest.mark.asyncio
async def test_save_locks_trainer_before_allocating_collection_number(
    monkeypatch,
) -> None:
    species = SpeciesBuilder().with_id(1).with_name("Bulbasaur").build()
    saved_row = {
        "id": 20,
        "collection_number": 5,
        "species_id": 1,
        "trainer_id": 99,
        "original_trainer_id": 99,
        "hp_iv": 31,
        "attack_iv": 31,
        "defense_iv": 31,
        "special_attack_iv": 31,
        "special_defense_iv": 31,
        "speed_iv": 31,
        "size": 1.0,
        "nature": "hardy",
        "is_shiny": False,
        "variant_id": None,
        "variant_name": None,
    }
    connection = _SaveFakeConnection(saved_row)
    fake_pool = _FakePool(connection)

    async def fake_get_pool():
        return fake_pool

    monkeypatch.setattr(
        "infrastructure.persistence.repositories.neon_creature_repository.get_pool",
        fake_get_pool,
    )
    species_repository = AsyncMock(spec=SpeciesRepository)
    species_repository.get = AsyncMock(return_value=species)
    repository = NeonCreatureRepository(species_repository=species_repository)

    creature = await repository.save(
        CreatureBuilder().with_species(species).with_trainer_id(99).build()
    )

    assert creature.collection_number == 5
    assert connection.events == [
        "transaction_enter",
        "lock",
        "max",
        "insert",
        "reload",
        "transaction_exit",
    ]
