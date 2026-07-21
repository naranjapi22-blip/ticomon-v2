from __future__ import annotations

import pytest

from core.rarity import Rarity
from infrastructure.species.neon_species_repository import NeonSpeciesRepository


class _Acquire:
    def __init__(self, connection) -> None:
        self._connection = connection

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


class _Pool:
    def __init__(self, connection) -> None:
        self._connection = connection

    def acquire(self):
        return _Acquire(self._connection)


class _Connection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    async def fetch(self, query: str, *args):
        self.calls.append((query, args))
        if "FROM species_variants" in query:
            return [
                {"species_id": 1, "id": 11, "name": "heat"},
                {"species_id": 1, "id": 12, "name": "wash"},
            ]
        rows = [
            {
                "id": 1,
                "pokeapi_id": 479,
                "name": "rotom",
                "type_1": "electric",
                "type_2": "ghost",
                "hp": 50,
                "attack": 50,
                "defense": 77,
                "special_attack": 95,
                "special_defense": 77,
                "speed": 91,
                "height": 3,
                "weight": 3,
                "capture_rate": 45,
                "spawn_rarity": "COMMON",
                "generation": 4,
                "is_baby": False,
                "is_legendary": False,
                "is_mythical": False,
            },
            {
                "id": 2,
                "pokeapi_id": 137,
                "name": "porygon",
                "type_1": "normal",
                "type_2": None,
                "hp": 65,
                "attack": 60,
                "defense": 70,
                "special_attack": 85,
                "special_defense": 75,
                "speed": 40,
                "height": 8,
                "weight": 365,
                "capture_rate": 45,
                "spawn_rarity": "COMMON",
                "generation": 1,
                "is_baby": False,
                "is_legendary": False,
                "is_mythical": False,
            },
        ]
        if "WHERE id = ANY" in query:
            requested = set(args[0])
            return [row for row in rows if row["id"] in requested]
        return rows


@pytest.mark.asyncio
async def test_find_many_by_names_loads_species_and_variants_in_two_queries(
    monkeypatch,
) -> None:
    connection = _Connection()

    async def get_pool():
        return _Pool(connection)

    monkeypatch.setattr(
        "infrastructure.species.neon_species_repository.get_pool",
        get_pool,
    )

    species_by_name = await NeonSpeciesRepository().find_many_by_names(
        ("rotom", "porygon", "missing", "rotom")
    )

    assert list(species_by_name) == ["rotom", "porygon"]
    assert [variant.name for variant in species_by_name["rotom"].variants] == [
        "heat",
        "wash",
    ]
    assert species_by_name["porygon"].variants == ()
    assert len(connection.calls) == 2
    assert connection.calls[0][1] == (["rotom", "porygon", "missing"],)
    assert connection.calls[1][1] == ([1, 2],)


@pytest.mark.asyncio
async def test_get_many_loads_variants_only_for_requested_species(monkeypatch) -> None:
    connection = _Connection()

    async def get_pool():
        return _Pool(connection)

    monkeypatch.setattr(
        "infrastructure.species.neon_species_repository.get_pool",
        get_pool,
    )

    await NeonSpeciesRepository().get_many([1])

    assert connection.calls[1][1] == ([1],)


@pytest.mark.asyncio
async def test_find_by_spawn_rarity_loads_variants_only_for_result(monkeypatch) -> None:
    connection = _Connection()

    async def get_pool():
        return _Pool(connection)

    monkeypatch.setattr(
        "infrastructure.species.neon_species_repository.get_pool",
        get_pool,
    )

    await NeonSpeciesRepository().find_by_spawn_rarity(Rarity.COMMON)

    assert connection.calls[1][1] == ([1, 2],)
