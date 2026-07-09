from abc import ABC, abstractmethod

from core.evolution.evolution_rule import EvolutionRule


class EvolutionRepository(ABC):
    """
    Repository for evolution rules.
    """

    @abstractmethod
    async def find_next(
        self,
        species_id: int,
    ) -> EvolutionRule | None:
        """
        Returns the next evolution rule for a species.
        """
        raise NotImplementedError
