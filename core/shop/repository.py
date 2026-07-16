from abc import ABC, abstractmethod

from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature


class ShopRepository(ABC):
    @abstractmethod
    async def purchase(
        self,
        trainer_id: int,
        creature: Creature,
        cost: CandyBundle,
        product_id: str,
        idempotency_key: str,
    ) -> tuple[Creature, CandyInventory, bool]:
        """Atomically charges candies and creates one shop creature."""
        raise NotImplementedError
