from core.candy.candy_repository import CandyRepository
from core.creature.creature_repository import CreatureRepository
from core.evolution.evolution_service import EvolutionService

from .evolution_application_result import EvolutionApplicationResult


class EvolutionApplicationService:
    """
    Orchestrates the evolution use case.
    """

    def __init__(
        self,
        evolution_service: EvolutionService,
        creature_repository: CreatureRepository,
        candy_repository: CandyRepository,
    ) -> None:
        self._evolution_service = evolution_service
        self._creature_repository = creature_repository
        self._candy_repository = candy_repository

    async def evolve(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> EvolutionApplicationResult:

        creature = await self._creature_repository.get(
            creature_id,
        )

        inventory = await self._candy_repository.get(
            trainer_id,
        )

        result = await self._evolution_service.evolve(
            creature=creature,
            inventory=inventory,
        )

        if result.success:

            creature = await self._creature_repository.save(
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
