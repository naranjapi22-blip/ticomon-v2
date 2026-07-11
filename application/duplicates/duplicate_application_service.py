from application.duplicates.duplicate_result import (
    DuplicateSpeciesResult,
)
from core.creature.creature_repository import CreatureRepository
from core.species.species_repository import SpeciesRepository


class DuplicateApplicationService:

    def __init__(
        self,
        creature_repository: CreatureRepository,
        species_repository: SpeciesRepository,
    ):
        self._creature_repository = creature_repository
        self._species_repository = species_repository

    async def get_duplicates(
        self,
        trainer_id: int,
    ) -> list[DuplicateSpeciesResult]:

        duplicates = await self._creature_repository.get_duplicate_species(
            trainer_id,
        )

        results = []

        for species_id, amount in duplicates:

            species = await self._species_repository.get(
                species_id,
            )

            results.append(
                DuplicateSpeciesResult(
                    species_id=species_id,
                    species_name=species.name,
                    amount=amount,
                )
            )

        return results
