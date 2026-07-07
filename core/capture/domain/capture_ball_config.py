from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaptureBallConfig:
    """
    Gameplay configuration associated with a Capture Ball.
    """

    weight: float
    modifier: float
