from abc import ABC, abstractmethod

from core.evolution.evolution_rule import EvolutionRule


class EvolutionRepository(ABC):
    """
    Repository for evolution rules.
    """

    @abstractmethod
    async def find_options(
        self,
        species_id: int,
    ) -> list[EvolutionRule]:
        """
        Returns all available evolution rules for a species.
        """
        raise NotImplementedError

    async def find_next(
        self,
        species_id: int,
    ) -> EvolutionRule | None:
        """
        Returns the first evolution rule for a species.

        Useful for linear evolutions.
        """

        options = await self.find_options(
            species_id,
        )

        if not options:
            return None

        return options[0]
