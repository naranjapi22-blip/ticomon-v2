from types import SimpleNamespace

import pytest

from scripts import repair_move_pp


class Connection:
    def __init__(self):
        self.updates = None

    async def fetch(self, query):
        return [{"id": "thunder"}, {"id": "missing-move"}]

    async def executemany(self, query, updates):
        self.updates = updates

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class Pool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return self.connection


@pytest.mark.asyncio
async def test_repair_uses_max_pp_and_skips_unknown_moves(monkeypatch):
    connection = Connection()
    monkeypatch.setattr(repair_move_pp, "get_pool", lambda: _pool(connection))
    monkeypatch.setattr(repair_move_pp, "close_pool", lambda: _close())
    monkeypatch.setattr(
        repair_move_pp,
        "Move",
        lambda move_id, gen: (
            SimpleNamespace(max_pp=16)
            if move_id == "thunder"
            else (_ for _ in ()).throw(KeyError(move_id))
        ),
    )

    result = await repair_move_pp.repair_move_pp()

    assert result == {"repaired": 1, "skipped": 1}
    assert connection.updates == [("thunder", 16)]


async def _pool(connection):
    return Pool(connection)


async def _close():
    return None
