from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from test.builders.species_builder import SpeciesBuilder


class CreatureBuilder:
    """
    Builder for creating Creature instances in tests.
    """

    def __init__(self):
        self._species = SpeciesBuilder().build()
        self._trainer_id = 1
        self._is_shiny = False
        self._id = None
        self._collection_number = None

    def with_species(
        self,
        species,
    ):
        self._species = species
        return self

    def with_trainer_id(
        self,
        trainer_id: int,
    ):
        self._trainer_id = trainer_id
        return self

    def shiny(self):
        self._is_shiny = True
        return self

    def build(self):

        return Creature(
            species=self._species,
            variant=None,
            trainer_id=self._trainer_id,
            ivs=IVs(
                hp=31,
                attack=31,
                defense=31,
                special_attack=31,
                special_defense=31,
                speed=31,
            ),
            size=Size(1.0),
            nature=Nature("hardy"),
            is_shiny=self._is_shiny,
            current_form=None,
            id=self._id,
            collection_number=self._collection_number,
        )

    def with_id(
        self,
        creature_id: int,
    ):
        self._id = creature_id
        return self

    def with_collection_number(
        self,
        collection_number: int,
    ):
        self._collection_number = collection_number
        return self
