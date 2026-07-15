from __future__ import annotations

import random
from dataclasses import dataclass, replace

from core.capture.domain.capture_ball import CaptureBall
from core.capture.domain.capture_chance_calculator import CaptureChanceCalculator
from core.opportunity.opportunity import Opportunity


@dataclass(frozen=True, slots=True)
class CaptureAttemptResult:
    success: bool
    chance: float
    roll: float
    opportunity: Opportunity
    capture_ball: CaptureBall


class CaptureAttemptService:
    def __init__(self, chance_calculator: CaptureChanceCalculator) -> None:
        self._chance_calculator = chance_calculator

    def attempt(
        self,
        opportunity: Opportunity,
        capture_ball: CaptureBall,
        random_source: random.Random,
        chance_override: float | None = None,
    ) -> CaptureAttemptResult:
        chance = (
            chance_override
            if chance_override is not None
            else self._chance_calculator.calculate(
                opportunity=opportunity,
                capture_ball=capture_ball,
            )
        )
        roll = random_source.random()
        success = roll < chance
        updated_opportunity = replace(
            opportunity,
            failed_attempts=opportunity.failed_attempts + (0 if success else 1),
        )
        return CaptureAttemptResult(
            success=success,
            chance=chance,
            roll=roll,
            opportunity=updated_opportunity,
            capture_ball=capture_ball,
        )
