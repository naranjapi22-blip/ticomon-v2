from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager

from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature


class ReleaseTransaction(ABC):
    @abstractmethod
    async def get_creatures_by_collection_numbers(
        self,
        trainer_id: int,
        collection_numbers: list[int] | tuple[int, ...],
    ) -> list[Creature]:
        """Loads and locks all creatures participating in the release."""
        raise NotImplementedError

    @abstractmethod
    async def get_candy_inventory(self, trainer_id: int) -> CandyInventory:
        """Loads and locks the trainer candy inventory."""
        raise NotImplementedError

    @abstractmethod
    async def get_assigned_creature_ids(
        self,
        trainer_id: int,
        creature_ids: list[int] | tuple[int, ...],
    ) -> set[int]:
        """Returns selected creature ids assigned to the trainer team."""
        raise NotImplementedError

    @abstractmethod
    async def delete_creatures(
        self,
        trainer_id: int,
        creatures: list[Creature] | tuple[Creature, ...],
    ) -> None:
        """Deletes the validated creatures in the current transaction."""
        raise NotImplementedError

    @abstractmethod
    async def save_candy_inventory(
        self,
        trainer_id: int,
        inventory: CandyInventory,
    ) -> None:
        """Persists candies in the current transaction."""
        raise NotImplementedError


class ReleaseUnitOfWork(ABC):
    @abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[ReleaseTransaction]:
        """Opens the atomic persistence boundary for a release."""
        raise NotImplementedError
