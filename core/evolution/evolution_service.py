from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_result import EvolutionResult
from core.evolution.evolution_rule import EvolutionRule
from core.species.species_repository import SpeciesRepository


class EvolutionService:
    """
    Executes creature evolutions.
    """

    def __init__(
        self,
        policy: EvolutionPolicy,
        species_repository: SpeciesRepository,
    ) -> None:
        self._policy = policy
        self._species_repository = species_repository

    async def evolve(
        self,
        creature: Creature,
        inventory: CandyInventory,
        rule: EvolutionRule,
    ) -> EvolutionResult:

        result = self._policy.validate(
            creature=creature,
            inventory=inventory,
            rule=rule,
        )

        if not result.success:
            return result

        evolved_species = await self._species_repository.get(
            rule.to_species_id,
        )

        inventory.consume(
            result.consumed_candies,
        )

        previous_species = creature.species

        creature.species = evolved_species
        self._preserve_matching_variant(creature, evolved_species)

        return EvolutionResult.succeeded(
            previous_species=previous_species,
            evolved_species=evolved_species,
            consumed_candies=result.consumed_candies,
        )

    def get_cost(
        self,
        rule: EvolutionRule,
    ):
        return self._policy.get_cost(
            rule,
        )

    async def get_species(
        self,
        species_id: int,
    ):
        return await self._species_repository.get(species_id)

    @staticmethod
    def _preserve_matching_variant(creature: Creature, evolved_species) -> None:
        if creature.current_form is None:
            return

        matching_variant = next(
            (
                variant
                for variant in evolved_species.variants or ()
                if variant.name == creature.current_form.name
            ),
            None,
        )
        if matching_variant is not None:
            creature.current_form = matching_variant
