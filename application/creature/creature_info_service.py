from core.creature.creature import Creature


class CreatureInfoService:
    """
    Application service used to retrieve creature information.
    """

    def __init__(
        self,
        creature_repository,
    ):
        self._creature_repository = creature_repository

    async def get_creature(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> Creature:
        """
        Returns one of the trainer's creatures.
        """

        return await self._creature_repository.get_by_collection_number(
            trainer_id,
            collection_number,
        )
