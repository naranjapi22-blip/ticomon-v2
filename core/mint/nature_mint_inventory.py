from dataclasses import dataclass


@dataclass(slots=True)
class NatureMintInventory:
    amount: int = 0

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Nature Mint amount cannot be negative.")

    def has_one(self) -> bool:
        return self.amount > 0

    def consume_one(self) -> None:
        if not self.has_one():
            raise ValueError("Insufficient Nature Mints.")
        self.amount -= 1
