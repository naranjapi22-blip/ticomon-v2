from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.rule_engine import RuleEngine
from core.spawn.weighted_selector import WeightedSelector
from core.species.species import Species
from core.species.species_repository import SpeciesRepository


class SpeciesSelector:
    """
    Coordinates the species selection process for a spawn.
    """

    def __init__(
        self,
        repository: SpeciesRepository,
        rule_engine: RuleEngine,
        weighted_selector: WeightedSelector,
    ) -> None:
        self._repository = repository
        self._rule_engine = rule_engine
        self._weighted_selector = weighted_selector

    async def select(
        self,
        context: SpawnContext,
        profile: SpawnProfile,
    ) -> tuple[Species, ...]:
        """
        Returns the species selected for the current spawn.
        """

        species_pool = await self._repository.get_all()

        valid_species = self._rule_engine.apply(
            species_pool,
            profile.rules,
            context,
            profile,
        )

        return self._weighted_selector.select(
            valid_species,
            profile.opportunity_count,
        )
