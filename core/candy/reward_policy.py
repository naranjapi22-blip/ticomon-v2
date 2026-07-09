from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from core.creature.creature import Creature


class RewardPolicy:
    """
    Calculates candy rewards for captured creatures.
    """

    def reward_for(
        self,
        creature: Creature,
    ) -> CandyBundle:

        evolution_chain = creature.species.evolution_chain

        if evolution_chain is None:
            stage = 1
        else:
            stage = evolution_chain.stage_of(
                creature.species.id,
            )

        reward = stage * 2

        candy_types = [CandyType(type_name) for type_name in creature.species.types]

        if len(candy_types) == 1:
            return CandyBundle.from_amounts(
                CandyAmount(
                    candy_types[0],
                    reward,
                )
            )

        split_reward = reward // 2

        return CandyBundle.from_amounts(
            CandyAmount(
                candy_types[0],
                split_reward,
            ),
            CandyAmount(
                candy_types[1],
                split_reward,
            ),
        )
