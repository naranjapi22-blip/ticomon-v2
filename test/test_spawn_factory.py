from core.spawn.spawn_factory import SpawnFactory
from core.species.evolution_chain import EvolutionChain
from core.species.species import Species


def test_create_spawn():

    chain = EvolutionChain(
        id=1,
        species=[],
        candy_requirements={}
    )

    pikachu = Species(
        id=25,
        name="Pikachu",
        generation=1,
        habitat="Forest",
        is_baby=False,
        is_legendary=False,
        is_mythical=False,
        types=["Electric"],
        base_stats={},
        height=4,
        weight=60,
        capture_rate=190,
        forms_switchable=False,
        evolution_chain=chain,
        variants=[],
    )

    eevee = Species(
        id=133,
        name="Eevee",
        generation=1,
        habitat="Urban",
        is_baby=False,
        is_legendary=False,
        is_mythical=False,
        types=["Normal"],
        base_stats={},
        height=3,
        weight=65,
        capture_rate=45,
        forms_switchable=False,
        evolution_chain=chain,
        variants=[],
    )

    spawn = SpawnFactory.create(
        id=1,
        species=[pikachu, eevee],
    )

    assert spawn.id == 1
    assert len(spawn.opportunities) == 2
    assert spawn.opportunities[0].species == pikachu
    assert spawn.opportunities[1].species == eevee