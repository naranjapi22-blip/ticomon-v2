from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType


class CandyMapper:
    """
    Maps persistence rows to CandyInventory.
    """

    def from_rows(
        self,
        rows,
    ) -> CandyInventory:

        candies = {CandyType(row["candy_type"]): row["amount"] for row in rows}

        return CandyInventory(
            _candies=candies,
        )

    def to_rows(
        self,
        inventory: CandyInventory,
    ) -> list[tuple[CandyType, int]]:

        return [(candy_type, amount) for candy_type, amount in inventory.items()]
