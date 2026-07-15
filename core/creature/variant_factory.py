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

        normalized_name = species.name.strip().casefold()
        chance = next(
            (
                chance
                for name, chance in SPECIAL_VARIANT_CHANCES.items()
                if name.strip().casefold() == normalized_name
            ),
            None,
        )

        if chance is not None:

            if random.random() >= chance:
                return None

        return random.choice(
            species.variants,
        )
