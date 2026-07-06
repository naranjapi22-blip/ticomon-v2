from core.creature.iv_factory import IVFactory
from core.creature.nature_factory import NatureFactory
from core.creature.shiny_factory import ShinyFactory
from core.creature.size_factory import SizeFactory
from core.creature.variant_factory import VariantFactory
from core.opportunity.opportunity import Opportunity
from core.species.species import Species


class OpportunityFactory:
    """
    Crea Opportunities a partir de una Species.
    """

    @staticmethod
    def create(species: Species) -> Opportunity:
        return Opportunity(
            species=species,
            variant=VariantFactory.create(species),
            ivs=IVFactory.create(),
            size=SizeFactory.create(),
            nature=NatureFactory.create(),
            is_shiny=ShinyFactory.create(),
            initial_form=None,
            interaction="capture",
        )
