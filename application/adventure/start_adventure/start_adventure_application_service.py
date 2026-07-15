from application.adventure.start_adventure.exceptions import (
    TrainerAlreadyExistsError,
)
from application.adventure.start_adventure.start_adventure_result import (
    StartAdventureResult,
)
from core.creature.creature_factory import CreatureFactory
from core.energy.trainer_energy_factory import TrainerEnergyFactory
from core.opportunity.opportunity_factory import OpportunityFactory
from core.trainer.trainer_factory import TrainerFactory


class StartAdventureApplicationService:

    def __init__(
        self,
        species_repository,
        creature_repository,
        trainer_repository,
        energy_repository,
    ):
        self._species_repository = species_repository
        self._creature_repository = creature_repository
        self._trainer_repository = trainer_repository
        self._energy_repository = energy_repository

    async def start(
        self,
        trainer_id: int,
        starter_species_id: int,
    ) -> StartAdventureResult:

        if await self._trainer_repository.exists(
            trainer_id,
        ):
            raise TrainerAlreadyExistsError()

        species = await self._species_repository.get(
            starter_species_id,
        )

        opportunity = OpportunityFactory.create(
            species,
        )

        creature = CreatureFactory.create(
            trainer_id=trainer_id,
            opportunity=opportunity,
        )

        # Save and reload the persisted creature.
        creature = await self._creature_repository.save(
            creature,
        )

        trainer = TrainerFactory.create(
            trainer_id=trainer_id,
            starter_creature_id=creature.id,
        )

        await self._trainer_repository.save(
            trainer,
        )
        trainer_energy = TrainerEnergyFactory.create(
            trainer_id=trainer.trainer_id,
        )

        await self._energy_repository.save(
            trainer_energy,
        )
        return StartAdventureResult(
            trainer=trainer,
            starter=creature,
        )
