import random

from core.rarity import Rarity


class RaritySelector:
    """
    Selects the spawn rarity according to the game's probability distribution.
    """

    _RARITIES = (
        Rarity.VERY_COMMON,
        Rarity.COMMON,
        Rarity.UNCOMMON,
        Rarity.RARE,
        Rarity.VERY_RARE,
        Rarity.EPIC,
        Rarity.LEGENDARY,
        Rarity.MYTHICAL,
    )

    _WEIGHTS = (
        35,  # VERY_COMMON
        25,  # COMMON
        20,  # UNCOMMON
        10,  # RARE
        6,  # VERY_RARE
        3,  # EPIC
        0.8,  # LEGENDARY
        0.2,  # MYTHICAL
    )

    def select(self) -> Rarity:
        """
        Returns a spawn rarity using the configured probability distribution.
        """

        return random.choices(
            self._RARITIES,
            weights=self._WEIGHTS,
            k=1,
        )[0]
