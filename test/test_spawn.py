from core.spawn.spawn import Spawn


def test_create_spawn():
    spawn = Spawn.create(id=1, opportunities=[])

    assert spawn.id == 1
    assert len(spawn.opportunities) == 0
