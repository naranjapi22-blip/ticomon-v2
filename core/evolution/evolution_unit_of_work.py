from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager

from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature


class EvolutionTransaction(ABC):
    @abstractmethod
    async def get_creature(self, trainer_id: int, collection_number: int) -> Creature:
        raise NotImplementedError

    @abstractmethod
    async def get_candy_inventory(self, trainer_id: int) -> CandyInventory:
        raise NotImplementedError

    @abstractmethod
    async def update_creature(self, creature: Creature) -> Creature:
        raise NotImplementedError

    @abstractmethod
    async def save_candy_inventory(
        self, trainer_id: int, inventory: CandyInventory
    ) -> None:
        raise NotImplementedError


class EvolutionUnitOfWork(ABC):
    @abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[EvolutionTransaction]:
        raise NotImplementedError
