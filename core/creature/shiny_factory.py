import random


class ShinyFactory:
    """
    Determina si una Opportunity será shiny.
    """

    SHINY_RATE = 1 / 1024

    @classmethod
    def create(cls) -> bool:
        return random.random() < cls.SHINY_RATE
