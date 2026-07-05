from core.opportunity.opportunity_factory import OpportunityFactory
from core.species.evolution_chain import EvolutionChain
from core.species.species import Species


def test_create_opportunity():
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
        forms_switchable=False,
        evolution_chain=chain,
        variants=[],
    )

    opportunity = OpportunityFactory.create(pikachu)

    assert opportunity.species == pikachu
    assert opportunity.interaction == "capture"