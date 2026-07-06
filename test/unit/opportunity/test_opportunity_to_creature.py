from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity_factory import OpportunityFactory


class FakeSpecies:
    """
    Species mínima para test sin depender de todo el sistema.
    """

    def __init__(self):
        self.name = "pikachu"
        self.default_form = "base"
        self.variants = []


def test_core_opportunity_to_creature_flow():
    # Arrange
    species = FakeSpecies()

    # Act
    opportunity = OpportunityFactory.create(species)

    creature = CreatureFactory.create(
        trainer_id=1,
        opportunity=opportunity,
    )

    # Assert - identidad base
    assert creature.species == opportunity.species
    assert creature.variant == opportunity.variant
    assert creature.ivs == opportunity.ivs
    assert creature.size == opportunity.size
    assert creature.nature == opportunity.nature
    assert creature.is_shiny == opportunity.is_shiny
    assert creature.current_form == opportunity.initial_form

    # Assert - ownership
    assert creature.trainer_id == 1
    assert creature.id is None
