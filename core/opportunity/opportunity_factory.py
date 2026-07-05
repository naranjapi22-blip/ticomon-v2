from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.opportunity.opportunity import Opportunity
from core.species.species import Species
from core.creature.iv_factory import IVFactory
from core.creature.nature_factory import NatureFactory
from core.creature.shiny_factory import ShinyFactory

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
            ivs=IVFactory.create(),
            size=1.0,
            nature=NatureFactory.create(),
            is_shiny=ShinyFactory.create(),
            initial_form=None,
            interaction="capture",
        )