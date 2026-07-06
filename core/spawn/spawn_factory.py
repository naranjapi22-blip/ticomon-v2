from core.opportunity.opportunity_factory import OpportunityFactory
from core.spawn.spawn import Spawn
from core.species.species import Species


class SpawnFactory:
    @staticmethod
    def create(
        id: int,
        species: list[Species],
    ) -> Spawn:
        opportunities = [OpportunityFactory.create(s) for s in species]

        return Spawn.create(
            id=id,
            opportunities=opportunities,
        )
