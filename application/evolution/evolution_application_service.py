import logging

from core.achievement.activity import AchievementActivity, AchievementActivityType
from core.candy.candy_repository import CandyRepository
from core.collection.history import CollectionEntrySource
from core.creature.creature_repository import CreatureRepository
from core.evolution.evolution_repository import EvolutionRepository
from core.evolution.evolution_service import EvolutionService

from .evolution_application_result import EvolutionApplicationResult
from .evolution_confirmation import EvolutionConfirmation

logger = logging.getLogger(__name__)


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
        achievement_activity_repository=None,
        achievement_award_service=None,
        collection_history_repository=None,
        evolution_unit_of_work=None,
    ) -> None:
        self._evolution_service = evolution_service
        self._evolution_repository = evolution_repository
        self._creature_repository = creature_repository
        self._candy_repository = candy_repository
        self._achievement_activity_repository = achievement_activity_repository
        self._achievement_award_service = achievement_award_service
        self._collection_history_repository = collection_history_repository
        self._evolution_unit_of_work = evolution_unit_of_work

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

        if self._evolution_unit_of_work is None:
            return await self._evolve_without_unit_of_work(
                trainer_id, collection_number, rule
            )
        async with self._evolution_unit_of_work.transaction() as transaction:
            creature = await transaction.get_creature(trainer_id, collection_number)
            inventory = await transaction.get_candy_inventory(trainer_id)
            result = await self._evolution_service.evolve(
                creature=creature, inventory=inventory, rule=rule
            )
            if result.success:
                creature = await transaction.update_creature(creature)
                await transaction.save_candy_inventory(trainer_id, inventory)
            return await self._finish_result(trainer_id, creature, result)

    async def _evolve_without_unit_of_work(
        self, trainer_id: int, collection_number: int, rule
    ) -> EvolutionApplicationResult:
        creature = await self._creature_repository.get_by_collection_number(
            trainer_id, collection_number
        )
        inventory = await self._candy_repository.get(trainer_id)
        result = await self._evolution_service.evolve(
            creature=creature, inventory=inventory, rule=rule
        )
        if result.success:
            creature = await self._creature_repository.update(creature)
            await self._candy_repository.save(trainer_id, inventory)
        return await self._finish_result(trainer_id, creature, result)

    async def _finish_result(self, trainer_id, creature, result):

        achievements = ()
        if result.success:

            if self._collection_history_repository is not None:
                try:
                    await self._collection_history_repository.record_creature(
                        creature,
                        CollectionEntrySource.EVOLUTION,
                    )
                except Exception:
                    logger.exception(
                        "evolution collection entry failed trainer_id=%s "
                        "creature_id=%s",
                        trainer_id,
                        creature.id,
                    )

            if (
                self._achievement_activity_repository is not None
                and self._achievement_award_service is not None
            ):
                activity = AchievementActivity(
                    trainer_id=trainer_id,
                    activity_type=AchievementActivityType.EVOLUTION,
                    idempotency_key=(
                        f"evolution:{creature.id or creature.collection_number}:"
                        f"{creature.species.id}"
                    ),
                    species_id=creature.species.id,
                )
                try:
                    if await self._achievement_activity_repository.record(activity):
                        achievements = (
                            await self._achievement_award_service.award_for_evolution(
                                trainer_id,
                                creature.species,
                            )
                        )
                except Exception:
                    logger.exception(
                        "evolution achievement award failed trainer_id=%s",
                        trainer_id,
                    )

        return EvolutionApplicationResult(
            success=result.success,
            creature=creature,
            previous_species=result.previous_species,
            evolved_species=result.evolved_species,
            consumed_candies=result.consumed_candies,
            failure_reason=result.failure_reason,
            achievements=achievements,
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
