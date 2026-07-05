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
        types=["electric"],
        base_stats={
            "hp": 35,
            "attack": 55,
            "defense": 40,
            "special_attack": 50,
            "special_defense": 50,
            "speed": 90,
        },
        height=4,
        weight=60,
        capture_rate=190,
        evolution_chain=chain,
        variants=[],
    )

    spawn = Spawn.create(
        id=1,
        opportunities=[]
    )

    assert spawn.id == 1
    assert len(spawn.opportunities) == 0
