import random
from core.opportunity.opportunity_factory import OpportunityFactory
from core.species.species_repository import SpeciesRepository


class SpawnService:

    def spawn(self):
        species_pool = SpeciesRepository.get_all()

        if not species_pool:
            raise Exception("No species available in DB")

        species = random.choice(species_pool)

        return OpportunityFactory.create(species)