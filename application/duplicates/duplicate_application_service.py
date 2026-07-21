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

        species_map = {
            species.id: species
            for species in await self._species_repository.get_many(
                [species_id for species_id, _ in duplicates]
            )
        }
        results = []

        for species_id, amount in duplicates:
            species = species_map.get(species_id)
            if species is None:
                continue

            results.append(
                DuplicateSpeciesResult(
                    species_id=species_id,
                    species_name=species.name,
                    amount=amount,
                )
            )

        return results

    async def get_duplicates_by_type(
        self,
        trainer_id: int,
        pokemon_type: str,
    ) -> list[DuplicateSpeciesResult]:

        raw_duplicates = await self._creature_repository.get_duplicate_species(
            trainer_id,
        )
        species_map = {
            species.id: species
            for species in await self._species_repository.get_many(
                [species_id for species_id, _ in raw_duplicates]
            )
        }

        results = []

        for species_id, amount in raw_duplicates:
            species = species_map.get(species_id)
            if species is None:
                continue

            if pokemon_type.lower() in [
                species_type.lower() for species_type in species.types
            ]:
                results.append(
                    DuplicateSpeciesResult(
                        species_id=species_id,
                        species_name=species.name,
                        amount=amount,
                    )
                )

        return results
