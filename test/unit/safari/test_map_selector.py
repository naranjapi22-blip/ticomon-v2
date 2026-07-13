from core.safari import (
    SAFARI_ZONE_DEFINITIONS,
    SafariMap,
    SafariMapInfluence,
    SafariMapSelector,
)


class FakeWeightedRandom:
    def __init__(self, selected_index: int = 0) -> None:
        self.selected_index = selected_index
        self.candidates = ()
        self.weights = ()

    def choices(self, candidates, weights, k):
        assert k == 1
        self.candidates = tuple(candidates)
        self.weights = tuple(weights)
        return [self.candidates[self.selected_index]]


def select_and_capture_weights(
    influence: SafariMapInfluence,
    selected_index: int = 0,
) -> tuple[SafariMap, FakeWeightedRandom]:
    random_source = FakeWeightedRandom(selected_index)
    selected = SafariMapSelector().select(
        influence,
        random_source,  # type: ignore[arg-type]
    )
    return selected, random_source


def test_empty_influence_keeps_all_maps_available_with_positive_weights():
    selected, random_source = select_and_capture_weights(SafariMapInfluence())

    assert selected == SafariMap.FOREST
    assert random_source.candidates == tuple(SafariMap)
    assert len(random_source.candidates) == 5
    assert all(weight > 0 for weight in random_source.weights)
    assert len(set(random_source.weights)) == 1


def test_water_influence_favors_coast_without_guaranteeing_it():
    selected, random_source = select_and_capture_weights(
        SafariMapInfluence({"water": 100}),
    )
    weights_by_map = dict(zip(random_source.candidates, random_source.weights))

    assert weights_by_map[SafariMap.COAST] > weights_by_map[SafariMap.SWAMP]
    assert weights_by_map[SafariMap.COAST] > weights_by_map[SafariMap.FOREST]
    assert selected == SafariMap.FOREST
    assert weights_by_map[SafariMap.FOREST] > 0


def test_influence_growth_is_capped_for_large_amounts():
    _, capped = select_and_capture_weights(SafariMapInfluence({"water": 100}))
    _, excessive = select_and_capture_weights(SafariMapInfluence({"water": 1_000_000}))

    assert excessive.weights == capped.weights
    assert max(excessive.weights) <= 3.0
    assert all(weight > 0 for weight in excessive.weights)


def test_total_influence_bonus_is_limited_across_many_types():
    all_types = {
        type_name: 1_000_000
        for type_name in {
            type_name
            for definition in SAFARI_ZONE_DEFINITIONS
            for type_name in definition.base_type_weights
        }
    }
    _, random_source = select_and_capture_weights(SafariMapInfluence(all_types))

    assert all(0 < weight <= 3.0 for weight in random_source.weights)


def test_fake_random_controls_map_result_and_returns_enum():
    selected, _ = select_and_capture_weights(SafariMapInfluence(), selected_index=4)

    assert selected == SafariMap.PLAINS
    assert isinstance(selected, SafariMap)
