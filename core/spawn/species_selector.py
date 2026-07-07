from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.rarity_selector import RaritySelector
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
        rarity_selector: RaritySelector,
        rule_engine: RuleEngine,
        weighted_selector: WeightedSelector,
    ) -> None:
        self._repository = repository
        self._rarity_selector = rarity_selector
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

        selected_species: list[Species] = []
        selected_ids: set[int] = set()

        while len(selected_species) < profile.opportunity_count:

            rarity = self._rarity_selector.select()

            species_pool = await self._repository.find_by_spawn_rarity(
                rarity,
            )

            valid_species = self._rule_engine.apply(
                species_pool,
                profile.rules,
                context,
                profile,
            )

            valid_species = tuple(
                species for species in valid_species if species.id not in selected_ids
            )

            if not valid_species:
                continue

            candidate = self._weighted_selector.select(
                valid_species,
                1,
            )[0]

            selected_species.append(candidate)
            selected_ids.add(candidate.id)

        return tuple(selected_species)
