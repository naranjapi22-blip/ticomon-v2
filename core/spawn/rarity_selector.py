import random

from core.spawn.spawn_rarity import SpawnRarity


class RaritySelector:
    """
    Selects the spawn rarity according to the game's probability distribution.
    """

    _RARITIES = (
        SpawnRarity.VERY_COMMON,
        SpawnRarity.COMMON,
        SpawnRarity.UNCOMMON,
        SpawnRarity.RARE,
        SpawnRarity.VERY_RARE,
        SpawnRarity.EPIC,
        SpawnRarity.LEGENDARY,
        SpawnRarity.MYTHICAL,
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

    def select(self) -> SpawnRarity:
        """
        Returns a spawn rarity using the configured probability distribution.
        """

        return random.choices(
            self._RARITIES,
            weights=self._WEIGHTS,
            k=1,
        )[0]
