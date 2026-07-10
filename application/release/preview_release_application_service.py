from application.release.preview_release_result import (
    PreviewReleaseResult,
)
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_repository import CandyRepository
from core.candy.reward_policy import RewardPolicy
from core.creature.creature_repository import CreatureRepository


class PreviewReleaseApplicationService:
    """
    Orchestrates the release preview use case.
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

    async def preview(
        self,
        trainer_id: int,
        collection_numbers: list[int],
    ) -> PreviewReleaseResult:

        creatures = []

        reward_bundle = CandyBundle()

        for collection_number in collection_numbers:

            creature = await self._creature_repository.get_by_collection_number(
                trainer_id,
                collection_number,
            )

            bundle = self._reward_policy.reward_for(
                creature,
            )

            reward_bundle = reward_bundle.merge(
                bundle,
            )

            creatures.append(
                creature,
            )

        return PreviewReleaseResult(
            creatures=creatures,
            reward_bundle=reward_bundle,
        )
