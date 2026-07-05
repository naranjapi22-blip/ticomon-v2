from core.opportunity.opportunity import Opportunity
from core.species.species import Species


class OpportunityFactory:
    """
    Crea Opportunities a partir de una Species.
    """

    @staticmethod
    def create(species: Species) -> Opportunity:
        return Opportunity(
            id=1,
            species=species,
            variant=None,
            ivs={},
            size=1.0,
            nature="",
            initial_form=None,
            interaction="capture",
        )