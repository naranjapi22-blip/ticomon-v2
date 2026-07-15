from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from core.species.species import Species


class AchievementRewardPolicy:
    """Builds achievement rewards from the species that caused an unlock."""

    def reward_for(self, species: Species, total_amount: int) -> CandyBundle:
        candy_types = tuple(CandyType(item.lower()) for item in species.types)

        if len(candy_types) == 1:
            return CandyBundle.from_amounts(CandyAmount(candy_types[0], total_amount))

        if len(candy_types) != 2 or total_amount % 2:
            raise ValueError("Achievement rewards require one or two species types.")

        amount_per_type = total_amount // 2
        return CandyBundle.from_amounts(
            CandyAmount(candy_types[0], amount_per_type),
            CandyAmount(candy_types[1], amount_per_type),
        )
