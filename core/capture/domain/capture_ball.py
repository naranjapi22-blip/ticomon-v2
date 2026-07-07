from enum import Enum


class CaptureBall(Enum):
    """
    Poké Balls that can be assigned by the game during a capture attempt.
    """

    POKE_BALL = "poke_ball"
    GREAT_BALL = "great_ball"
    ULTRA_BALL = "ultra_ball"
    MASTER_BALL = "master_ball"
