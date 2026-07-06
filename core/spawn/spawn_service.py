from core.opportunity.opportunity_factory import OpportunityFactory
from core.species.species_repository import SpeciesRepository


class SpawnService:
    """
    Creates spawn opportunities from registered species.
    """

    def __init__(
        self,
        repository: SpeciesRepository,
    ) -> None:
        self._repository = repository

    async def spawn(self):
        species_pool = await self._repository.get_all()

        if not species_pool:
            raise ValueError("No species available.")

        species = species_pool[0]

        return OpportunityFactory.create(species)
