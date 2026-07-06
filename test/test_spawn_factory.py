from core.spawn.spawn_factory import SpawnFactory
from test.factories import create_species


def test_create_spawn():
    pikachu = create_species(
        id=25,
        name="Pikachu",
    )

    eevee = create_species(
        id=133,
        name="Eevee",
        types=["normal"],
        capture_rate=45,
    )

    spawn = SpawnFactory.create(
        id=1,
        species=[pikachu, eevee],
    )

    assert spawn.id == 1
    assert len(spawn.opportunities) == 2
    assert spawn.opportunities[0].species == pikachu
    assert spawn.opportunities[1].species == eevee
