import random

from core.species.species import Species
from core.species.variant import Variant


class VariantFactory:
    """
    Responsible for selecting the cosmetic variant of a Species.
    """

    PIKACHU_ID = 25
    PIKACHU_VARIANT_CHANCE = 0.02

    def create(
        self,
        species: Species,
    ) -> Variant | None:

        if not species.variants:
            return None

        if species.pokeapi_id == self.PIKACHU_ID:
            if random.random() >= self.PIKACHU_VARIANT_CHANCE:
                return None

        return random.choice(species.variants)
