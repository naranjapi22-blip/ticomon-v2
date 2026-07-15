from core.creature.creature import Creature
from core.opportunity.opportunity import Opportunity


class CreatureFactory:
    """
    Builds a Creature from an Opportunity.

    Capture does not modify the Pokémon's characteristics; it only assigns a
    Trainer and creates a persistent entity.
    """

    def create(
        self,
        trainer_id: int,
        opportunity: Opportunity,
    ) -> Creature:
        return Creature(
            species=opportunity.species,
            trainer_id=trainer_id,
            ivs=opportunity.ivs,
            size=opportunity.size,
            nature=opportunity.nature,
            is_shiny=opportunity.is_shiny,
            current_form=opportunity.initial_form,
            original_trainer_id=trainer_id,
        )
