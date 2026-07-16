from abc import ABC, abstractmethod

from core.creature.creature import Creature
from core.creature.nature import Nature
from core.mint.nature_mint_inventory import NatureMintInventory


class NatureMintRepository(ABC):
    @abstractmethod
    async def get(self, trainer_id: int) -> NatureMintInventory:
        raise NotImplementedError

    @abstractmethod
    async def apply(
        self,
        trainer_id: int,
        collection_number: int,
        minted_nature: Nature | None,
    ) -> tuple[Creature, int]:
        """Atomically applies one mint and returns the creature and remaining amount."""
        raise NotImplementedError
