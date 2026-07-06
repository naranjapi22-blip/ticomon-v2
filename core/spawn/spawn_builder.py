from core.opportunity.opportunity_factory import OpportunityFactory
from core.spawn.spawn import Spawn
from core.species.species import Species


class SpawnBuilder:
    @staticmethod
    def create(
        species: list[Species],
    ) -> Spawn:
        opportunities = [OpportunityFactory.create(s) for s in species]

        return Spawn.create(
            opportunities=opportunities,
        )
