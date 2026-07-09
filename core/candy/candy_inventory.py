from dataclasses import dataclass, field

from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType


@dataclass(slots=True)
class CandyInventory:
    """
    Represents a trainer's candy inventory.
    """

    _candies: dict[CandyType, int] = field(default_factory=dict)

    def get_amount(
        self,
        candy_type: CandyType,
    ) -> int:
        return self._candies.get(candy_type, 0)

    def has(
        self,
        bundle: CandyBundle,
    ) -> bool:
        return all(
            self.get_amount(candy_type) >= amount
            for candy_type, amount in bundle.items()
        )

    def add(
        self,
        bundle: CandyBundle,
    ) -> None:
        for candy_type, amount in bundle.items():
            self._candies[candy_type] = self.get_amount(candy_type) + amount

    def consume(
        self,
        bundle: CandyBundle,
    ) -> None:
        if not self.has(bundle):
            raise ValueError("Insufficient candies.")

        for candy_type, amount in bundle.items():
            self._candies[candy_type] = self.get_amount(candy_type) - amount

    def items(
        self,
    ):
        return self._candies.items()

    def is_empty(
        self,
    ) -> bool:
        return len(self._candies) == 0
