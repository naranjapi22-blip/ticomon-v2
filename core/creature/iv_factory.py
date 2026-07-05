import random

from core.creature.ivs import IVs


class IVFactory:
    """
    Genera IVs para una nueva Creature u Opportunity.
    """

    @staticmethod
    def create() -> IVs:
        return IVs(
            hp=random.randint(0, 31),
            attack=random.randint(0, 31),
            defense=random.randint(0, 31),
            special_attack=random.randint(0, 31),
            special_defense=random.randint(0, 31),
            speed=random.randint(0, 31),
        )