import pytest

from core.safari import (
    SAFARI_VALID_WEATHER_BY_MAP,
    WEATHER_WEIGHTS,
    SafariMap,
    SafariWeather,
    SafariWeatherSelector,
)


class FakeWeightedRandom:
    def __init__(self, selected_index: int = 0) -> None:
        self.selected_index = selected_index
        self.candidates = ()
        self.weights = ()
        self.call_count = 0

    def choices(self, candidates, weights, k):
        assert k == 1
        self.call_count += 1
        self.candidates = tuple(candidates)
        self.weights = tuple(weights)
        return [self.candidates[self.selected_index]]


@pytest.mark.parametrize("safari_map", tuple(SafariMap))
def test_each_map_returns_only_configured_weather(safari_map):
    valid_weather = SAFARI_VALID_WEATHER_BY_MAP[safari_map]

    for index, expected in enumerate(valid_weather):
        random_source = FakeWeightedRandom(index)
        selected = SafariWeatherSelector().select(
            safari_map,
            random_source,  # type: ignore[arg-type]
        )
        assert selected == expected
        assert selected in valid_weather
        assert isinstance(selected, SafariWeather)


def test_snow_only_appears_for_configured_maps():
    maps_with_snow = {
        safari_map
        for safari_map, weather in SAFARI_VALID_WEATHER_BY_MAP.items()
        if SafariWeather.SNOW in weather
    }

    assert maps_with_snow == {SafariMap.MOUNTAIN}


def test_clear_uses_configured_weight_and_fake_random_controls_result():
    random_source = FakeWeightedRandom(0)

    selected = SafariWeatherSelector().select(
        SafariMap.COAST,
        random_source,  # type: ignore[arg-type]
    )

    assert selected == SafariWeather.CLEAR
    assert random_source.weights[0] == WEATHER_WEIGHTS[SafariWeather.CLEAR]


def test_clear_is_fallback_when_map_has_no_weather_configuration(monkeypatch):
    monkeypatch.setitem(SAFARI_VALID_WEATHER_BY_MAP, SafariMap.FOREST, ())
    random_source = FakeWeightedRandom()

    selected = SafariWeatherSelector().select(
        SafariMap.FOREST,
        random_source,  # type: ignore[arg-type]
    )

    assert selected == SafariWeather.CLEAR
    assert random_source.call_count == 0


def test_invalid_weather_weights_and_impossible_configuration_fail(monkeypatch):
    monkeypatch.setitem(WEATHER_WEIGHTS, SafariWeather.CLEAR, 0)
    with pytest.raises(ValueError, match="weights"):
        SafariWeatherSelector().select(
            SafariMap.FOREST,
            FakeWeightedRandom(),  # type: ignore[arg-type]
        )

    monkeypatch.setitem(
        SAFARI_VALID_WEATHER_BY_MAP,
        SafariMap.COAST,
        (SafariWeather.RAIN,),
    )
    with pytest.raises(ValueError, match="include CLEAR"):
        SafariWeatherSelector().select(
            SafariMap.COAST,
            FakeWeightedRandom(),  # type: ignore[arg-type]
        )
