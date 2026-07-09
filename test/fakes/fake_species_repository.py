from core.species.species import Species
from core.species.species_repository import SpeciesRepository


class FakeSpeciesRepository(SpeciesRepository):
    """
    In-memory species repository for tests.
    """

    def __init__(
        self,
        *species: Species,
    ) -> None:
        self._species = {item.id: item for item in species}

    async def get(
        self,
        species_id: int,
    ) -> Species:
        return self._species[species_id]

    async def find_by_name(
        self,
        name: str,
    ) -> Species | None:
        for species in self._species.values():
            if species.name == name:
                return species

        return None

    async def get_all(
        self,
    ) -> list[Species]:
        return list(
            self._species.values(),
        )

    async def find_by_spawn_rarity(
        self,
        rarity,
    ) -> list[Species]:
        return [
            species
            for species in self._species.values()
            if species.spawn_rarity == rarity
        ]
