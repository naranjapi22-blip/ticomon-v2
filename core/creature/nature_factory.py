import random

from core.creature.nature import Nature


class NatureFactory:
    """
    Genera una Nature aleatoria.
    """

    _NATURES = [
        "hardy",
        "lonely",
        "brave",
        "adamant",
        "naughty",
        "bold",
        "docile",
        "relaxed",
        "impish",
        "lax",
        "timid",
        "hasty",
        "serious",
        "jolly",
        "naive",
        "modest",
        "mild",
        "quiet",
        "bashful",
        "rash",
        "calm",
        "gentle",
        "sassy",
        "careful",
        "quirky",
    ]

    @classmethod
    def create(cls) -> Nature:
        return Nature(random.choice(cls._NATURES))