from enum import Enum


class SpawnRarity(str, Enum):
    VERY_COMMON = "VERY_COMMON"
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    VERY_RARE = "VERY_RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"
    MYTHICAL = "MYTHICAL"
