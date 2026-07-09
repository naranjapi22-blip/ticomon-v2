from dataclasses import dataclass

from core.candy.candy_type import CandyType


@dataclass(frozen=True, slots=True)
class CandyAmount:
    """
    Represents an amount of a specific candy type.
    """

    type: CandyType
    amount: int

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("Candy amount must be greater than zero.")
