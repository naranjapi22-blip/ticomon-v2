from abc import ABC, abstractmethod

from core.rarity import Rarity
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
    async def find_many_by_names(
        self,
        names: list[str] | tuple[str, ...],
    ) -> dict[str, Species]: ...

    @abstractmethod
    async def get_all(self) -> tuple[Species, ...]: ...

    @abstractmethod
    async def find_by_spawn_rarity(
        self,
        rarity: Rarity,
    ) -> tuple[Species, ...]:
        """
        Returns every species belonging to the given spawn rarity.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_many(
        self,
        species_ids: list[int] | tuple[int, ...],
    ) -> list[Species]: ...
