from abc import ABC, abstractmethod

from core.creature.creature import Creature


class CreatureRepository(ABC):
    """
    Defines how Creature entities are persisted.
    """

    @abstractmethod
    async def save(
        self,
        creature: Creature,
    ) -> Creature:
        """
        Persists a Creature and returns the stored entity.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        creature_id: int,
    ) -> Creature:
        """
        Returns a Creature by its identifier.
        """
        raise NotImplementedError

    @abstractmethod
    async def has_species(
        self,
        trainer_id: int,
        species_id: int,
    ) -> bool:
        """
        Returns whether the trainer has already captured the species.
        """
        raise NotImplementedError
