from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType


class CandyBuilder:
    """
    Builder for creating CandyBundle instances in tests.
    """

    def __init__(self):
        self._candies = {}

    def with_candy(
        self,
        candy_type: CandyType,
        amount: int,
    ):
        self._candies[candy_type] = amount
        return self

    def fire(
        self,
        amount: int,
    ):
        return self.with_candy(
            CandyType.FIRE,
            amount,
        )

    def build(self) -> CandyBundle:

        return CandyBundle.from_amounts(
            *[
                CandyAmount(
                    candy_type,
                    amount,
                )
                for candy_type, amount in self._candies.items()
            ]
        )
