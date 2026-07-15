from unittest.mock import patch

from core.creature.creature_factory import CreatureFactory
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.opportunity.opportunity import Opportunity
from core.opportunity.opportunity_factory import OpportunityFactory
from core.species.variant import Variant
from test.factories import create_species


def test_create_creature():
    species = create_species(
        id=25,
        name="Pikachu",
    )

    opportunity = Opportunity(
        species=species,
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
        initial_form=Variant(
            id=1,
            name="Rockstar",
        ),
        interaction="capture",
    )
    creature = CreatureFactory.create(
        trainer_id=50,
        opportunity=opportunity,
    )

    assert creature.trainer_id == 50
    assert creature.original_trainer_id == 50
    assert creature.species is species
    assert creature.current_form == opportunity.initial_form
    assert creature.current_form.name == "Rockstar"
    assert creature.ivs == opportunity.ivs
    assert creature.size == opportunity.size
    assert creature.nature == opportunity.nature
    assert creature.is_shiny is True


def test_create_creature_preserves_normal_form_as_none():
    species = create_species(
        id=658,
        name="greninja",
        variants=[Variant(id=128, name="ash")],
    )

    with patch("random.random", return_value=0.005):
        opportunity = OpportunityFactory.create(species)

    creature = CreatureFactory.create(
        trainer_id=50,
        opportunity=opportunity,
    )

    assert opportunity.initial_form is None
    assert creature.current_form is None
