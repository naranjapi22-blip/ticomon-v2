from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_result import EvolutionResult
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
    ) -> EvolutionResult:

        result = self._policy.validate(
            creature=creature,
            inventory=inventory,
        )

        if not result.success:
            return result

        chain = creature.species.evolution_chain
        assert chain is not None

        evolved_species = await self._species_repository.get(
            chain.next_species_of(
                creature.species.id,
            )
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
