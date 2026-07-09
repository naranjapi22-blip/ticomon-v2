from core.opportunity.opportunity import Opportunity
from test.builders.species_builder import SpeciesBuilder


class OpportunityBuilder:
    """
    Builder for creating Opportunity instances in tests.
    """

    def __init__(self):
        self._species = SpeciesBuilder().build()
        self._trainer_id = None

    def with_species(
        self,
        species,
    ):
        self._species = species
        return self

    def build(self) -> Opportunity:

        return Opportunity(
            id=1,
            species=self._species,
            variant=None,
            ivs=None,
            size=None,
            nature=None,
            is_shiny=False,
            initial_form=None,
        )
