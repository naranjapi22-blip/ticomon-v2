from __future__ import annotations

from core.safari.domain import SafariMap, SafariPhase, SafariTimeOfDay, SafariWeather

MAP_INTRO: dict[SafariMap, str] = {
    SafariMap.FOREST: "The expedition slips beneath a dense green canopy.",
    SafariMap.MOUNTAIN: "A cold ridge rises ahead of the party.",
    SafariMap.COAST: "Salt air and surf frame the next stretch of Safari.",
    SafariMap.SWAMP: "Mud and mist blur the edges of the trail.",
    SafariMap.PLAINS: "An open horizon stretches across the route.",
}

WEATHER_NOTE: dict[SafariWeather, str] = {
    SafariWeather.CLEAR: "The weather stays clear for now.",
    SafariWeather.RAIN: "Rain taps softly across the expedition.",
    SafariWeather.FOG: "A thin fog hangs over the area.",
    SafariWeather.STORM: "The sky crackles with restless energy.",
    SafariWeather.SNOW: "Cold air sharpens every movement.",
}

TIME_NOTE: dict[SafariTimeOfDay, str] = {
    SafariTimeOfDay.DAY: "Daylight keeps the way visible.",
    SafariTimeOfDay.SUNSET: "Sunset paints the Safari in warm tones.",
    SafariTimeOfDay.NIGHT: "Night deepens the atmosphere around the group.",
}

PHASE_NOTE: dict[SafariPhase, str] = {
    SafariPhase.START: "The Safari is just beginning.",
    SafariPhase.DEVELOPMENT: "The expedition pushes deeper into the route.",
    SafariPhase.FINAL: "The final stretch of the Safari is at hand.",
}


def encounter_narrative(
    safari_map: SafariMap,
    weather: SafariWeather,
    time_of_day: SafariTimeOfDay,
    phase: SafariPhase,
) -> str:
    return " ".join(
        (
            MAP_INTRO[safari_map],
            WEATHER_NOTE[weather],
            TIME_NOTE[time_of_day],
            PHASE_NOTE[phase],
        )
    )


def summary_narrative(finish_reason: str, encounters_completed: int) -> str:
    return (
        f"The expedition ends after {encounters_completed} encounter(s). "
        f"Final reason: {finish_reason.lower().replace('_', ' ')}."
    )


def route_narrative(safari_map: SafariMap, options_count: int) -> str:
    return (
        f"The {safari_map.value.lower()} route forks into {options_count} option(s). "
        "The party weighs the next move carefully."
    )
