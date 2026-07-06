from abc import ABC, abstractmethod

from core.spawn.spawn_rarity import SpawnRarity
from core.species.species import Species


class SpeciesRepository(ABC):
    """
    Defines how Species are retrieved from a data source.
    """

    @abstractmethod
    async def get(self, species_id: int) -> Species: ...

    @abstractmethod
    async def find_by_name(self, name: str) -> Species | None: ...

    @abstractmethod
    async def get_all(self) -> tuple[Species, ...]: ...

    @abstractmethod
    async def find_by_spawn_rarity(
        self,
        rarity: SpawnRarity,
    ) -> tuple[Species, ...]:
        """
        Returns every species belonging to the given spawn rarity.
        """
        raise NotImplementedError
