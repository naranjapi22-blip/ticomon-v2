from application.pokedex.dto import (
    PokedexDTO,
    PokedexEntryDTO,
)


class PokedexService:
    """
    Returns the trainer Pokédex.
    """

    def __init__(
        self,
        species_repository,
        creature_repository,
    ):
        self._species_repository = species_repository
        self._creature_repository = creature_repository

    async def get_pokedex(
        self,
        trainer_id: int,
    ) -> PokedexDTO:

        species = await self._species_repository.get_all()

        discovered = await self._creature_repository.get_discovered_species(
            trainer_id,
        )

        entries = tuple(
            PokedexEntryDTO(
                species=entry,
                discovered=entry.id in discovered,
            )
            for entry in species
        )

        return PokedexDTO(
            entries=entries,
        )
