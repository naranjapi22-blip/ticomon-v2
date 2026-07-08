from abc import ABC, abstractmethod

from core.creature.creature import Creature


class ProfileRepository(ABC):
    """
    Defines how trainer profile information is persisted.
    """

    @abstractmethod
    async def get_featured_creature(
        self,
        trainer_id: int,
    ) -> Creature | None:
        raise NotImplementedError

    @abstractmethod
    async def set_featured_creature(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> None:
        raise NotImplementedError
