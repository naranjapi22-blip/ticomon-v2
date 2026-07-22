from application.release.exceptions import ReleaseCreatureAssignedToTeam
from application.release.release_result import ReleaseResult
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_repository import CandyRepository
from core.candy.reward_policy import RewardPolicy
from core.creature.creature_repository import CreatureRepository
from core.release.release_unit_of_work import ReleaseUnitOfWork
from core.team.team_repository import TeamRepository


class ReleaseApplicationService:
    """
    Orchestrates the release use case.
    """

    def __init__(
        self,
        creature_repository: CreatureRepository,
        candy_repository: CandyRepository,
        reward_policy: RewardPolicy,
        unit_of_work: ReleaseUnitOfWork | None = None,
        team_repository: TeamRepository | None = None,
    ) -> None:
        self._creature_repository = creature_repository
        self._candy_repository = candy_repository
        self._reward_policy = reward_policy
        self._unit_of_work = unit_of_work
        self._team_repository = team_repository

    async def release(
        self,
        trainer_id: int,
        collection_numbers: list[int],
    ) -> ReleaseResult:

        if len(collection_numbers) != len(set(collection_numbers)):
            raise ValueError("Collection numbers must be unique.")

        if self._unit_of_work is not None:
            async with self._unit_of_work.transaction() as transaction:
                released_creatures = (
                    await transaction.get_creatures_by_collection_numbers(
                        trainer_id,
                        collection_numbers,
                    )
                )
                assigned_ids = await transaction.get_assigned_creature_ids(
                    trainer_id,
                    [creature.id for creature in released_creatures],
                )
                self._raise_if_assigned(released_creatures, assigned_ids)
                inventory = await transaction.get_candy_inventory(trainer_id)
                reward_bundle = CandyBundle()

                for creature in released_creatures:
                    bundle = self._reward_policy.reward_for(creature)
                    reward_bundle = reward_bundle.merge(bundle)
                    inventory.add(bundle)

                await transaction.delete_creatures(trainer_id, released_creatures)
                await transaction.save_candy_inventory(trainer_id, inventory)

            return ReleaseResult(
                success=True,
                released_creatures=released_creatures,
                reward_bundle=reward_bundle,
            )

        creatures = await self._creature_repository.get_by_collection_numbers(
            trainer_id,
            collection_numbers,
        )
        if self._team_repository is not None:
            assigned_ids = await self._team_repository.get_assigned_creature_ids(
                trainer_id,
                [creature.id for creature in creatures],
            )
            self._raise_if_assigned(creatures, assigned_ids)
        inventory = await self._candy_repository.get(trainer_id)

        released_creatures = creatures

        reward_bundle = CandyBundle()

        for creature in creatures:
            bundle = self._reward_policy.reward_for(
                creature,
            )

            reward_bundle = reward_bundle.merge(
                bundle,
            )

            inventory.add(
                bundle,
            )

        await self._creature_repository.delete_many(trainer_id, released_creatures)

        await self._candy_repository.save(
            trainer_id,
            inventory,
        )

        return ReleaseResult(
            success=True,
            released_creatures=released_creatures,
            reward_bundle=reward_bundle,
        )

    @staticmethod
    def _raise_if_assigned(creatures, assigned_ids: set[int]) -> None:
        collection_numbers = [
            creature.collection_number
            for creature in creatures
            if creature.id in assigned_ids
        ]
        if collection_numbers:
            raise ReleaseCreatureAssignedToTeam(collection_numbers)
