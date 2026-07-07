from core.rarity.rarity import Rarity
from core.rarity.rarity_config import RarityConfig

RARITY_CONFIG = {
    Rarity.VERY_COMMON: RarityConfig(
        spawn_weight=35,
    ),
    Rarity.COMMON: RarityConfig(
        spawn_weight=25,
    ),
    Rarity.UNCOMMON: RarityConfig(
        spawn_weight=20,
    ),
    Rarity.RARE: RarityConfig(
        spawn_weight=10,
    ),
    Rarity.VERY_RARE: RarityConfig(
        spawn_weight=6,
    ),
    Rarity.EPIC: RarityConfig(
        spawn_weight=3,
    ),
    Rarity.LEGENDARY: RarityConfig(
        spawn_weight=0.8,
    ),
    Rarity.MYTHICAL: RarityConfig(
        spawn_weight=0.2,
    ),
}
