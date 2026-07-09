from core.candy.candy_inventory import CandyInventory
from core.candy.candy_repository import CandyRepository


class FakeCandyRepository(CandyRepository):
    """
    In-memory candy repository for tests.
    """

    def __init__(
        self,
        inventory: CandyInventory | None = None,
    ) -> None:
        self._inventory = inventory or CandyInventory()

        self.saved: list[tuple[int, CandyInventory]] = []

    async def get(
        self,
        trainer_id: int,
    ) -> CandyInventory:
        return self._inventory

    async def save(
        self,
        trainer_id: int,
        inventory: CandyInventory,
    ) -> None:
        self._inventory = inventory

        self.saved.append(
            (
                trainer_id,
                inventory,
            )
        )
