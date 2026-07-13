from __future__ import annotations

import random

from core.safari.domain import TIME_OF_DAY_WEIGHTS, SafariTimeOfDay


class SafariTimeOfDaySelector:
    def select(self, random_source: random.Random) -> SafariTimeOfDay:
        times = tuple(TIME_OF_DAY_WEIGHTS)
        if not times or any(not isinstance(value, SafariTimeOfDay) for value in times):
            raise ValueError("Safari time-of-day configuration is invalid.")

        weights = tuple(TIME_OF_DAY_WEIGHTS[value] for value in times)
        if any(weight <= 0 for weight in weights):
            raise ValueError("Safari time-of-day weights must be positive.")

        return random_source.choices(times, weights=weights, k=1)[0]
