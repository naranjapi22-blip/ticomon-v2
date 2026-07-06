from abc import ABC, abstractmethod

from core.spawn.context import SpawnContext
from core.species.species import Species


class Rule(ABC):
    """
    Determines whether a species is eligible for a spawn.
    """

    @abstractmethod
    def allows(
        self,
        species: Species,
        context: SpawnContext,
    ) -> bool:
        """
        Returns True if the species is allowed to participate
        in the current spawn.
        """
        raise NotImplementedError
