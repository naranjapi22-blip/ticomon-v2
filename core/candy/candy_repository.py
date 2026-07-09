from abc import ABC, abstractmethod

from core.candy.candy_inventory import CandyInventory


class CandyRepository(ABC):
    """
    Repository responsible for persisting trainer candy inventories.
    """

    @abstractmethod
    async def get(
        self,
        trainer_id: int,
    ) -> CandyInventory:
        """
        Returns the trainer's candy inventory.
        """
        raise NotImplementedError

    @abstractmethod
    async def save(
        self,
        trainer_id: int,
        inventory: CandyInventory,
    ) -> None:
        """
        Persists the trainer's candy inventory.
        """
        raise NotImplementedError
