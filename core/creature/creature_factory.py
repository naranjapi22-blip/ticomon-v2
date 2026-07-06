from core.creature.creature import Creature
from core.opportunity.opportunity import Opportunity


class CreatureFactory:
    """
    Crea una Creature a partir de una Opportunity capturada.
    """

    @staticmethod
    def create(
        creature_id: int,
        trainer_id: int,
        opportunity: Opportunity,
    ) -> Creature:
        return Creature(
            id=creature_id,
            species=opportunity.species,
            variant=opportunity.variant,
            trainer_id=trainer_id,
            ivs=opportunity.ivs,
            size=opportunity.size,
            nature=opportunity.nature,
            is_shiny=opportunity.is_shiny,
            current_form=opportunity.initial_form,
        )
