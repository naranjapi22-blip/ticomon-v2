from core.candy.candy_repository import CandyRepository
from core.creature.creature_repository import CreatureRepository
from core.evolution.evolution_repository import EvolutionRepository
from core.evolution.evolution_service import EvolutionService

from .evolution_application_result import EvolutionApplicationResult
from .evolution_confirmation import EvolutionConfirmation


class EvolutionApplicationService:
    """
    Orchestrates the evolution use case.
    """

    def __init__(
        self,
        evolution_service: EvolutionService,
        evolution_repository: EvolutionRepository,
        creature_repository: CreatureRepository,
        candy_repository: CandyRepository,
    ) -> None:
        self._evolution_service = evolution_service
        self._evolution_repository = evolution_repository
        self._creature_repository = creature_repository
        self._candy_repository = candy_repository

    async def get_options(
        self,
        trainer_id: int,
        collection_number: int,
    ):
        creature = await self._creature_repository.get_by_collection_number(
            trainer_id,
            collection_number,
        )

        return await self._evolution_repository.find_options(
            creature.species.id,
        )

    async def evolve(
        self,
        trainer_id: int,
        collection_number: int,
        rule,
    ) -> EvolutionApplicationResult:

        creature = await self._creature_repository.get_by_collection_number(
            trainer_id,
            collection_number,
        )

        inventory = await self._candy_repository.get(
            trainer_id,
        )

        result = await self._evolution_service.evolve(
            creature=creature,
            inventory=inventory,
            rule=rule,
        )

        if result.success:

            creature = await self._creature_repository.update(
                creature,
            )

            await self._candy_repository.save(
                trainer_id,
                inventory,
            )

        return EvolutionApplicationResult(
            success=result.success,
            creature=creature,
            previous_species=result.previous_species,
            evolved_species=result.evolved_species,
            consumed_candies=result.consumed_candies,
            failure_reason=result.failure_reason,
        )

    async def get_confirmation(
        self,
        trainer_id: int,
        collection_number: int,
        rule,
    ) -> EvolutionConfirmation:

        creature = await self._creature_repository.get_by_collection_number(
            trainer_id,
            collection_number,
        )

        inventory = await self._candy_repository.get(
            trainer_id,
        )

        evolved_species = await self._evolution_service.get_species(
            rule.to_species_id,
        )

        cost = self._evolution_service.get_cost(
            rule,
        )

        return EvolutionConfirmation(
            previous_species=creature.species,
            evolved_species=evolved_species,
            cost=cost,
            current_candies=inventory.get_amount(
                cost.type,
            ),
        )
