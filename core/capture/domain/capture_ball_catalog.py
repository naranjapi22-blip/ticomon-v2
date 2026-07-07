from core.capture.domain.capture_ball import CaptureBall
from core.capture.domain.capture_ball_config import CaptureBallConfig

CAPTURE_BALL_CONFIG = {
    CaptureBall.POKE_BALL: CaptureBallConfig(
        weight=70,
        modifier=1.0,
    ),
    CaptureBall.GREAT_BALL: CaptureBallConfig(
        weight=20,
        modifier=1.20,
    ),
    CaptureBall.ULTRA_BALL: CaptureBallConfig(
        weight=9.8,
        modifier=1.40,
    ),
    CaptureBall.MASTER_BALL: CaptureBallConfig(
        weight=0.2,
        modifier=255.0,
    ),
}
