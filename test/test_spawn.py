from core.spawn.spawn import Spawn
from core.species.species import Species
from core.species.evolution_chain import EvolutionChain


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
        habitat="forest",
        is_baby=False,
        is_legendary=False,
        is_mythical=False,
        types=["electric"],
        base_stats={},
        height=4,
        weight=60,
        capture_rate=190,
        forms_switchable=False,
        evolution_chain=chain,
        variants=[],
    )

    spawn = Spawn.create(
        id=1,
        opportunities=[]
    )

    assert spawn.id == 1
    assert len(spawn.opportunities) == 0