from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from core.spawn.context import SpawnContext
from core.species.species import Species

if TYPE_CHECKING:
    from core.spawn.profile import SpawnProfile


class Rule(ABC):
    """
    Determines whether a species is eligible for a spawn.
    """

    @abstractmethod
    def allows(
        self,
        species: Species,
        context: SpawnContext,
        profile: SpawnProfile,
    ) -> bool:
        """
        Returns True if the species is allowed
        for the current spawn.
        """
        raise NotImplementedError
