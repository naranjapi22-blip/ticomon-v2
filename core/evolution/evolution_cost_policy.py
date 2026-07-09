from core.candy.candy_amount import CandyAmount
from core.candy.candy_type import CandyType


class EvolutionCostPolicy:
    """
    Calculates candy cost from evolution tier.
    """

    TIER_COSTS = {
        "basic": 10,
        "standard": 20,
        "advanced": 40,
        "exceptional": 100,
    }

    def calculate(
        self,
        candy_type: CandyType,
        tier: str,
    ) -> CandyAmount:

        return CandyAmount(
            candy_type,
            self.TIER_COSTS[tier],
        )
