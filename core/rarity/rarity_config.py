from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RarityConfig:
    """
    Gameplay configuration associated with a rarity.
    """

    spawn_weight: float
    base_capture: float
    fatigue_bonus: float
    capture_cap: float
