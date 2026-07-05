from dataclasses import dataclass


@dataclass
class IVs:
    """
    Representa los Individual Values de una Creature.
    """

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int