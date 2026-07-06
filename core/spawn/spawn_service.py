from core.opportunity.opportunity import Opportunity
from core.opportunity.opportunity_factory import OpportunityFactory
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.species_selector import SpeciesSelector


class SpawnService:
    """
    Orchestrates the spawn generation process.
    """

    def __init__(
        self,
        selector: SpeciesSelector,
    ) -> None:
        self._selector = selector

    async def spawn(
        self,
        context: SpawnContext,
        profile: SpawnProfile,
    ) -> tuple[Opportunity, ...]:
        """
        Generates the spawn opportunities for the current context.
        """

        species = await self._selector.select(
            context,
            profile,
        )

        return tuple(OpportunityFactory.create(candidate) for candidate in species)
