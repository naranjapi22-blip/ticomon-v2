from core.spawn.spawn import Spawn


def test_create_spawn():
    spawn = Spawn.create(opportunities=[])

    assert len(spawn.opportunities) == 0
