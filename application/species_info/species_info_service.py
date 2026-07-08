from application.species_info.dto import SpeciesInfoDTO


class SpeciesInfoService:
    """
    Returns information about a species for a specific trainer.
    """

    def __init__(
        self,
        species_repository,
        creature_repository,
    ):
        self._species_repository = species_repository
        self._creature_repository = creature_repository

    async def get_species_info(
        self,
        trainer_id: int,
        species_name: str,
    ) -> SpeciesInfoDTO:
        species = await self._species_repository.find_by_name(
            species_name,
        )

        if species is None:
            raise ValueError(f"Species '{species_name}' was not found.")

        creatures = await self._creature_repository.get_by_species(
            trainer_id,
            species.id,
        )

        return SpeciesInfoDTO(
            species=species,
            creatures=tuple(creatures),
        )
