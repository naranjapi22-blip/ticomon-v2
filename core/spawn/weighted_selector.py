from abc import ABC, abstractmethod

from core.species.species import Species


class WeightedSelector(ABC):
    """
    Selects species from a collection using
    a weighted selection strategy.
    """

    @abstractmethod
    def select(
        self,
        species: tuple[Species, ...],
        amount: int,
    ) -> tuple[Species, ...]:
        """
        Selects the requested number of species.
        """
        raise NotImplementedError
