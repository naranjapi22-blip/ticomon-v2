from application.profile.trainer_profile_dto import TrainerProfileDTO
from application.trainer.trainer_catalog import get_trainer


class ProfileService:
    POKEDEX_SIZE = 1077

    def __init__(
        self,
        creature_repository,
        profile_repository,
    ):
        self._creature_repository = creature_repository
        self._profile_repository = profile_repository

    async def get_profile(
        self,
        trainer_id: int,
    ) -> TrainerProfileDTO:

        total_captured = await self._creature_repository.count_creatures(
            trainer_id,
        )

        unique_species = await self._creature_repository.count_species(
            trainer_id,
        )

        shiny_count = await self._creature_repository.count_shinies(
            trainer_id,
        )

        featured_creature = None

        featured_creature_id = await self._profile_repository.get_featured_creature_id(
            trainer_id,
        )

        if featured_creature_id is not None:
            featured_creature = await self._creature_repository.get(
                featured_creature_id,
            )

        selected_trainer = await self._profile_repository.get_selected_trainer(
            trainer_id,
        )

        trainer = get_trainer(
            selected_trainer,
        )

        completion_percentage = unique_species / self.POKEDEX_SIZE * 100

        return TrainerProfileDTO(
            trainer_id=trainer_id,
            trainer=trainer,
            total_captured=total_captured,
            unique_species=unique_species,
            shiny_count=shiny_count,
            completion_percentage=completion_percentage,
            featured_creature=featured_creature,
        )

    async def set_featured_creature(
        self,
        trainer_id: int,
        collection_number: int,
    ) -> None:
        """
        Sets the trainer's featured creature.
        """

        creature = await self._creature_repository.get_by_collection_number(
            trainer_id,
            collection_number,
        )

        await self._profile_repository.set_featured_creature(
            trainer_id,
            creature.id,
        )

    async def set_trainer(
        self,
        trainer_id: int,
        selected_trainer: int,
    ) -> None:
        """
        Sets the trainer avatar.
        """

        await self._profile_repository.set_selected_trainer(
            trainer_id,
            selected_trainer,
        )
