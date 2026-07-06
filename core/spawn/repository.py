from abc import ABC, abstractmethod

from core.species.species import Species


class SpeciesRepository(ABC):
    """
    Defines how Species are retrieved from a data source.
    """

    @abstractmethod
    def get(self, species_id: int) -> Species:
        """
        Returns a species by its identifier.
        """
        raise NotImplementedError

    @abstractmethod
    def find_by_name(self, name: str) -> Species | None:
        """
        Returns a species by name, or None if it does not exist.
        """
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> tuple[Species, ...]:
        """
        Returns all registered species.
        """
        raise NotImplementedError
