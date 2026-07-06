from core.creature.creature import Creature
from core.opportunity.opportunity import Opportunity


class CreatureFactory:
    """
    Construye una Creature a partir de una Opportunity.

    La captura no modifica las características del Pokémon; únicamente le
    asigna un Trainer y crea una entidad persistente.
    """

    def create(
        self,
        trainer_id: int,
        opportunity: Opportunity,
    ) -> Creature:
        return Creature(
            species=opportunity.species,
            variant=opportunity.variant,
            trainer_id=trainer_id,
            ivs=opportunity.ivs,
            size=opportunity.size,
            nature=opportunity.nature,
            is_shiny=opportunity.is_shiny,
            current_form=opportunity.initial_form,
        )
