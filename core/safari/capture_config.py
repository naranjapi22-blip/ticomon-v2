from types import MappingProxyType

from core.rarity import Rarity

SAFARI_BASE_CAPTURE = MappingProxyType(
    {
        Rarity.COMMON: 0.21,
        Rarity.UNCOMMON: 0.15,
        Rarity.RARE: 0.0925,
        Rarity.VERY_RARE: 0.055,
    }
)
