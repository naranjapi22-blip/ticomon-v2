import random

from core.species.species import Species
from core.species.variant import Variant

SPECIAL_VARIANT_CHANCES = {
    "Pikachu": 0.005,
    "Greninja": 0.005,
}


class VariantFactory:
    """
    Creates cosmetic variants for a species.
    """

    @staticmethod
    def create(
        species: Species,
    ) -> Variant | None:

        if not species.variants:
            return None

        chance = SPECIAL_VARIANT_CHANCES.get(
            species.name,
        )

        if chance is not None:

            if random.random() >= chance:
                return None

        return random.choice(
            species.variants,
        )
