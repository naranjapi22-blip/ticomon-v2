import pytest

from core.safari import (
    TIME_OF_DAY_WEIGHTS,
    SafariTimeOfDay,
    SafariTimeOfDaySelector,
)


class FakeWeightedRandom:
    def __init__(self, selected_index: int) -> None:
        self.selected_index = selected_index
        self.candidates = ()
        self.weights = ()

    def choices(self, candidates, weights, k):
        assert k == 1
        self.candidates = tuple(candidates)
        self.weights = tuple(weights)
        return [self.candidates[self.selected_index]]


@pytest.mark.parametrize(
    ("selected_index", "expected"),
    list(enumerate(TIME_OF_DAY_WEIGHTS)),
)
def test_selector_uses_configured_times_and_fake_random(selected_index, expected):
    random_source = FakeWeightedRandom(selected_index)

    selected = SafariTimeOfDaySelector().select(
        random_source,  # type: ignore[arg-type]
    )

    assert selected == expected
    assert isinstance(selected, SafariTimeOfDay)
    assert random_source.candidates == tuple(TIME_OF_DAY_WEIGHTS)
    assert random_source.weights == tuple(TIME_OF_DAY_WEIGHTS.values())


def test_selector_rejects_non_positive_weight(monkeypatch):
    monkeypatch.setitem(TIME_OF_DAY_WEIGHTS, SafariTimeOfDay.DAY, 0)

    with pytest.raises(ValueError, match="weights"):
        SafariTimeOfDaySelector().select(
            FakeWeightedRandom(0),  # type: ignore[arg-type]
        )
