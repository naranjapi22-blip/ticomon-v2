from core.creature.creature import Creature
from core.creature.factory import CreatureFactory
from core.creature.repository import CreatureRepository
from core.opportunity.opportunity import Opportunity


class CaptureUseCase:
    """
    Caso de uso encargado de capturar una Opportunity.
    """

    def __init__(
        self,
        creature_factory: CreatureFactory,
        creature_repository: CreatureRepository,
    ) -> None:
        self._creature_factory = creature_factory
        self._creature_repository = creature_repository

    async def execute(
        self,
        trainer_id: int,
        opportunity: Opportunity,
    ) -> Creature:
        creature = self._creature_factory.create(
            trainer_id=trainer_id,
            opportunity=opportunity,
        )

        return await self._creature_repository.save(creature)
