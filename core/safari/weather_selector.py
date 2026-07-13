from __future__ import annotations

import random

from core.safari.domain import (
    SAFARI_VALID_WEATHER_BY_MAP,
    WEATHER_WEIGHTS,
    SafariMap,
    SafariWeather,
)


class SafariWeatherSelector:
    def select(
        self,
        safari_map: SafariMap,
        random_source: random.Random,
    ) -> SafariWeather:
        if not isinstance(safari_map, SafariMap):
            raise ValueError("safari_map must be a SafariMap.")

        valid_weather = SAFARI_VALID_WEATHER_BY_MAP.get(safari_map, ())
        if not valid_weather:
            return SafariWeather.CLEAR
        if SafariWeather.CLEAR not in valid_weather:
            raise ValueError("Safari weather configuration must include CLEAR.")

        weights = []
        for weather in valid_weather:
            if not isinstance(weather, SafariWeather):
                raise ValueError("Safari weather configuration is invalid.")
            weight = WEATHER_WEIGHTS.get(weather)
            if weight is None or weight <= 0:
                raise ValueError("Safari weather weights must be positive.")
            weights.append(weight)

        return random_source.choices(valid_weather, weights=weights, k=1)[0]
