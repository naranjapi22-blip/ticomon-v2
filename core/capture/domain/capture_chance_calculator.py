from core.capture.domain.capture_ball import CaptureBall
from core.capture.domain.capture_ball_catalog import CAPTURE_BALL_CONFIG
from core.opportunity.opportunity import Opportunity
from core.rarity.rarity_catalog import RARITY_CONFIG


class CaptureChanceCalculator:
    """
    Calculates the probability of capturing an Opportunity.
    """

    def calculate(
        self,
        opportunity: Opportunity,
        capture_ball: CaptureBall,
    ) -> float:
        rarity = RARITY_CONFIG[opportunity.species.spawn_rarity]
        ball = CAPTURE_BALL_CONFIG[capture_ball]

        if capture_ball is CaptureBall.MASTER_BALL:
            return 1.0

        capture_rate_modifier = (opportunity.species.capture_rate / 255.0) ** 0.5

        chance = rarity.base_capture

        chance *= capture_rate_modifier
        chance *= ball.modifier

        chance += opportunity.failed_attempts * rarity.fatigue_bonus

        return min(
            chance,
            rarity.capture_cap,
        )
