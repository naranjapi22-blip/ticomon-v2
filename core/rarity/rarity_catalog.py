from core.rarity.rarity import Rarity
from core.rarity.rarity_config import RarityConfig

RARITY_CONFIG = {
    Rarity.VERY_COMMON: RarityConfig(
        spawn_weight=35,
        base_capture=0.10,
        fatigue_bonus=0.020,
        capture_cap=0.45,
    ),
    Rarity.COMMON: RarityConfig(
        spawn_weight=25,
        base_capture=0.07,
        fatigue_bonus=0.015,
        capture_cap=0.45,
    ),
    Rarity.UNCOMMON: RarityConfig(
        spawn_weight=20,
        base_capture=0.05,
        fatigue_bonus=0.010,
        capture_cap=0.45,
    ),
    Rarity.RARE: RarityConfig(
        spawn_weight=10,
        base_capture=0.03,
        fatigue_bonus=0.008,
        capture_cap=0.45,
    ),
    Rarity.VERY_RARE: RarityConfig(
        spawn_weight=6,
        base_capture=0.0225,
        fatigue_bonus=0.0065,
        capture_cap=0.45,
    ),
    Rarity.EPIC: RarityConfig(
        spawn_weight=3,
        base_capture=0.015,
        fatigue_bonus=0.005,
        capture_cap=0.45,
    ),
    Rarity.LEGENDARY: RarityConfig(
        spawn_weight=0.8,
        base_capture=0.002,
        fatigue_bonus=0.002,
        capture_cap=0.30,
    ),
    Rarity.MYTHICAL: RarityConfig(
        spawn_weight=0.2,
        base_capture=0.005,
        fatigue_bonus=0.003,
        capture_cap=0.30,
    ),
}
