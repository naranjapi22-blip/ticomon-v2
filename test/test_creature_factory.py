from core.creature.creature_factory import CreatureFactory
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.opportunity.opportunity import Opportunity
from core.species.evolution_chain import EvolutionChain
from core.species.species import Species
from core.species.variant import Variant


def test_create_creature():
    chain = EvolutionChain(id=1, species=[], candy_requirements={})

    species = Species(
        id=25,
        name="Pikachu",
        types=["Electric"],
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

    opportunity = Opportunity(
        id=1,
        species=species,
        variant=Variant(id=1, name="Rockstar"),
        ivs=IVs(
            hp=31,
            attack=31,
            defense=31,
            special_attack=31,
            special_defense=31,
            speed=31,
        ),
        size=Size(1.10),
        nature=Nature("adamant"),
        is_shiny=True,
        initial_form=None,
        interaction="capture",
    )

    creature = CreatureFactory.create(
        creature_id=100,
        trainer_id=50,
        opportunity=opportunity,
    )

    assert creature.id == 100
    assert creature.trainer_id == 50
    assert creature.species is species
    assert creature.variant == opportunity.variant
    assert creature.ivs == opportunity.ivs
    assert creature.size == opportunity.size
    assert creature.nature == opportunity.nature
    assert creature.is_shiny is True
