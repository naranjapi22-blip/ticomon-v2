import random


class ShinyFactory:
    """
    Determines whether an Opportunity will be shiny.
    """

    SHINY_RATE = 1 / 1024

    @classmethod
    def create(cls) -> bool:
        return random.random() < cls.SHINY_RATE
