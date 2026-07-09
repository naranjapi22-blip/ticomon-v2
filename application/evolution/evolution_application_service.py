from application.evolution.evolution_application_result import (
    EvolutionApplicationResult,
)
from core.candy.candy_repository import CandyRepository
from core.creature.creature_repository import CreatureRepository
from core.evolution.evolution_service import EvolutionService


class EvolutionApplicationService:
    """
    Coordinates creature evolutions.
    """

    def __init__(
        self,
        creature_repository: CreatureRepository,
        candy_repository: CandyRepository,
        evolution_service: EvolutionService,
    ) -> None:
        self._creature_repository = creature_repository
        self._candy_repository = candy_repository
        self._evolution_service = evolution_service

    async def evolve(
        self,
        creature_id: int,
    ) -> EvolutionApplicationResult:

        creature = await self._creature_repository.get(
            creature_id,
        )

        inventory = await self._candy_repository.get(
            creature.trainer_id,
        )

        result = await self._evolution_service.evolve(
            creature,
            inventory,
        )

        if hasattr(result, "evolved_species"):
            await self._creature_repository.save(
                creature,
            )

            await self._candy_repository.save(
                creature.trainer_id,
                inventory,
            )

        return EvolutionApplicationResult(
            evolution=result,
        )
