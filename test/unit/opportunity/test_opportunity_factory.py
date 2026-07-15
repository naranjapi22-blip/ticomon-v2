from unittest.mock import patch

from core.opportunity.opportunity_factory import OpportunityFactory
from core.species.variant import Variant
from test.factories import create_species


def test_create_opportunity():
    pikachu = create_species(
        id=25,
        name="Pikachu",
    )

    opportunity = OpportunityFactory.create(pikachu)

    assert opportunity.species == pikachu
    assert opportunity.interaction == "capture"


def test_create_opportunity_keeps_normal_form_for_lowercase_greninja():
    greninja = create_species(
        id=658,
        name="greninja",
        variants=[Variant(id=128, name="ash")],
    )

    with patch("random.random", return_value=0.005):
        opportunity = OpportunityFactory.create(greninja)

    assert opportunity.initial_form is None
