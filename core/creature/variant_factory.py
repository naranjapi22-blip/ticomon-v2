import random

from core.species.species import Species
from core.species.variant import Variant


class VariantFactory:
    PROBABILITY = 0.02

    @classmethod
    def create(cls, species: Species) -> Variant | None:
        if not species.variants:
            return None

        if random.random() > cls.PROBABILITY:
            return None

        return random.choice(species.variants)
