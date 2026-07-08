from abc import ABC, abstractmethod


class ProfileRepository(ABC):
    """
    Defines how trainer profile information is persisted.
    """

    @abstractmethod
    async def get_featured_creature_id(
        self,
        trainer_id: int,
    ) -> int | None:
        """
        Returns the identifier of the trainer's featured creature.
        """
        raise NotImplementedError

    @abstractmethod
    async def set_featured_creature(
        self,
        trainer_id: int,
        creature_id: int,
    ) -> None:
        """
        Persists the trainer's featured creature.
        """
        raise NotImplementedError
