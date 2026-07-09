from enum import Enum, auto


class EvolutionFailureReason(Enum):
    """
    Describes why an evolution could not be completed.
    """

    FINAL_STAGE = auto()
    NOT_ENOUGH_CANDIES = auto()
