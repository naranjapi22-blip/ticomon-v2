from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from datetime import date

from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.safari.unlock import SafariUnlock
from core.safari.world import SafariWorld


class CaptureTransaction(ABC):
    @abstractmethod
    async def save_creature(self, creature: Creature) -> Creature:
        """Persists a captured creature with its next collection number."""

    @abstractmethod
    async def get_candy_inventory(self, trainer_id: int) -> CandyInventory:
        """Loads the trainer candy inventory within this transaction."""

    @abstractmethod
    async def save_candy_inventory(
        self,
        trainer_id: int,
        inventory: CandyInventory,
    ) -> None:
        """Persists the trainer candy inventory within this transaction."""

    @abstractmethod
    async def get_or_create_world(
        self,
        guild_id: int,
        reset_date: date,
    ) -> SafariWorld:
        """Locks and returns the guild world, creating its initial state."""

    @abstractmethod
    async def save_world(self, world: SafariWorld) -> SafariWorld:
        """Persists the already locked world state."""

    @abstractmethod
    async def save_unlock(self, unlock: SafariUnlock) -> SafariUnlock:
        """Appends an unlock to the persistent FIFO queue."""


class CaptureUnitOfWork(ABC):
    @abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[CaptureTransaction]:
        """Opens the atomic persistence boundary for a successful capture."""
