import logging

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType
from core.creature.creature import Creature

logger = logging.getLogger(__name__)


def evolution_stage(creature: Creature) -> int:
    """Return the creature's normalized position in its evolution chain."""
    chain = creature.species.evolution_chain
    if chain is None:
        return 1
    try:
        stage = int(chain.stage_of(creature.species.id))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        logger.warning(
            "Invalid evolution chain; using base candy reward species_id=%s",
            creature.species.id,
        )
        return 1
    if stage < 1:
        logger.warning(
            "Invalid evolution stage; using base candy reward species_id=%s stage=%s",
            creature.species.id,
            stage,
        )
        return 1
    return min(stage, 3)


class RewardPolicy:
    """Calculates the shared candy reward for captures and releases."""

    def reward_for(self, creature: Creature) -> CandyBundle:
        stage = evolution_stage(creature)
        total = stage * 2
        names = list(dict.fromkeys(creature.species.types))
        if not names or len(names) > 2:
            raise ValueError("A species must have one or two distinct types.")

        try:
            candy_types = [CandyType(name.casefold()) for name in names]
        except (AttributeError, ValueError) as error:
            raise ValueError("A species contains an unknown type.") from error

        if len(candy_types) == 1:
            return CandyBundle.from_amounts(CandyAmount(candy_types[0], total))

        split = total // 2
        return CandyBundle.from_amounts(
            CandyAmount(candy_types[0], split),
            CandyAmount(candy_types[1], split),
        )
