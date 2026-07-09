from application.release.release_result import ReleaseResult
from core.candy.candy_repository import CandyRepository
from core.candy.reward_policy import RewardPolicy
from core.creature.creature_repository import CreatureRepository


class ReleaseApplicationService:
    """
    Orchestrates the release use case.
    """

    def __init__(
        self,
        creature_repository: CreatureRepository,
        candy_repository: CandyRepository,
        reward_policy: RewardPolicy,
    ) -> None:
        self._creature_repository = creature_repository
        self._candy_repository = candy_repository
        self._reward_policy = reward_policy

    async def release(
        self,
        trainer_id: int,
        collection_numbers: list[int],
    ):

        creature = await self._creature_repository.get_by_collection_number(
            trainer_id,
            collection_numbers[0],
        )

        inventory = await self._candy_repository.get(
            trainer_id,
        )

        reward_bundle = self._reward_policy.reward_for(
            creature,
        )

        inventory.add(
            reward_bundle,
        )

        await self._creature_repository.delete(
            creature,
        )

        await self._candy_repository.save(
            trainer_id,
            inventory,
        )

        return ReleaseResult(
            success=True,
            released_creatures=[creature],
            reward_bundle=reward_bundle,
        )
