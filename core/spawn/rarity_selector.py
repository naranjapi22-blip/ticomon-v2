import random

from core.rarity import RARITY_CONFIG, Rarity


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

    @property
    def _weights(self) -> tuple[float, ...]:
        return tuple(RARITY_CONFIG[rarity].spawn_weight for rarity in self._RARITIES)

    def select(self) -> Rarity:
        """
        Returns a spawn rarity using the configured probability distribution.
        """

        return random.choices(
            self._RARITIES,
            weights=self._weights,
            k=1,
        )[0]
