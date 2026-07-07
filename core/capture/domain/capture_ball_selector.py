import random

from core.capture.domain.capture_ball import CaptureBall
from core.capture.domain.capture_ball_catalog import CAPTURE_BALL_CONFIG


class CaptureBallSelector:
    """
    Selects a Capture Ball according to its configured weight.
    """

    def select(self) -> CaptureBall:
        balls = list(CAPTURE_BALL_CONFIG.keys())

        weights = [CAPTURE_BALL_CONFIG[ball].weight for ball in balls]

        return random.choices(
            population=balls,
            weights=weights,
            k=1,
        )[0]
