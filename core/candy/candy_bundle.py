from dataclasses import dataclass, field

from core.candy.candy_amount import CandyAmount
from core.candy.candy_type import CandyType


@dataclass(frozen=True, slots=True)
class CandyBundle:
    """
    Represents a collection of candy amounts.
    """

    _amounts: dict[CandyType, int] = field(default_factory=dict)

    @classmethod
    def from_amounts(
        cls,
        *amounts: CandyAmount,
    ) -> "CandyBundle":
        candies: dict[CandyType, int] = {}

        for candy in amounts:
            candies[candy.type] = candies.get(candy.type, 0) + candy.amount

        return cls(_amounts=candies)

    def get(
        self,
        candy_type: CandyType,
    ) -> int:
        return self._amounts.get(candy_type, 0)

    def is_empty(
        self,
    ) -> bool:
        return len(self._amounts) == 0

    def items(
        self,
    ):
        return self._amounts.items()

    def __contains__(
        self,
        candy_type: CandyType,
    ) -> bool:
        return candy_type in self._amounts
