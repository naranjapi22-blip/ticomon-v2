from core.opportunity.opportunity_factory import OpportunityFactory
from test.factories import create_species


def test_create_opportunity():
    pikachu = create_species(
        id=25,
        name="Pikachu",
    )

    opportunity = OpportunityFactory.create(pikachu)

    assert opportunity.species == pikachu
    assert opportunity.interaction == "capture"
