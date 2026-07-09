from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_repository import EvolutionRepository
from core.evolution.evolution_result import EvolutionResult
from core.species.species_repository import SpeciesRepository


class EvolutionService:
    """
    Executes creature evolutions.
    """

    def __init__(
        self,
        policy: EvolutionPolicy,
        evolution_repository: EvolutionRepository,
        species_repository: SpeciesRepository,
    ) -> None:
        self._policy = policy
        self._evolution_repository = evolution_repository
        self._species_repository = species_repository

    async def evolve(
        self,
        creature: Creature,
        inventory: CandyInventory,
    ) -> EvolutionResult:

        rule = await self._evolution_repository.find_next(
            creature.species.id,
        )

        if rule is None:
            return EvolutionResult.failed_final_stage(
                creature.species,
            )

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

        return EvolutionResult.succeeded(
            previous_species=previous_species,
            evolved_species=evolved_species,
            consumed_candies=result.consumed_candies,
        )
