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
