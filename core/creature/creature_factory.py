from core.creature.creature import Creature


class CreatureFactory:

    @staticmethod
    def create(
        trainer_id,
        opportunity,
    ):
        return Creature(
            species=opportunity.species,
            trainer_id=trainer_id,
            ivs=opportunity.ivs,
            size=opportunity.size,
            nature=opportunity.nature,
            is_shiny=opportunity.is_shiny,
            current_form=opportunity.initial_form,
            id=None,
            collection_number=None,
            original_trainer_id=trainer_id,
        )
