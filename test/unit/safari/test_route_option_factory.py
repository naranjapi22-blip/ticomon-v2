from core.safari import (
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariRouteConfigurationError,
    SafariRouteOption,
    SafariRouteOptionFactory,
    SafariThematicEvent,
    SafariZone,
)


class FakeWeightedRandom:
    def __init__(self, option_count: int = 3) -> None:
        self._option_count = option_count
        self.weight_calls: list[tuple[float, ...]] = []

    def choice(self, candidates):
        assert self._option_count in candidates
        return self._option_count

    def choices(self, candidates, weights, k):
        assert k == 1
        self.weight_calls.append(tuple(weights))
        return [candidates[0]]


def make_stay_option(zone: SafariZone) -> SafariRouteOption:
    definition = SAFARI_ZONE_DEFINITION_BY_ZONE[zone]
    return SafariRouteOption(
        id=f"{zone.value}:{zone.value}",
        source_zone=zone,
        destination_zone=zone,
        type_weight_modifiers=definition.base_type_weights,
        allowed_events=definition.allowed_events,
        narrative_key=f"{zone.value.lower()}_to_{zone.value.lower()}",
    )


def test_factory_returns_two_to_three_unique_valid_destinations():
    random_source = FakeWeightedRandom()
    options = SafariRouteOptionFactory().create_options(
        current_zone=SafariZone.FOREST_ENTRANCE,
        visited_zones=(),
        previous_option=None,
        random_source=random_source,  # type: ignore[arg-type]
    )
    definition = SAFARI_ZONE_DEFINITION_BY_ZONE[SafariZone.FOREST_ENTRANCE]

    assert 2 <= len(options) <= 3
    assert len({option.id for option in options}) == len(options)
    assert len({option.destination_zone for option in options}) == len(options)
    assert all(option.source_zone == SafariZone.FOREST_ENTRANCE for option in options)
    assert all(
        option.destination_zone in definition.transitions
        or option.destination_zone == SafariZone.FOREST_ENTRANCE
        for option in options
    )
    assert all(
        SAFARI_ZONE_DEFINITION_BY_ZONE[option.destination_zone].safari_map
        == definition.safari_map
        for option in options
    )


def test_single_transition_zone_combines_transition_with_stay():
    options = SafariRouteOptionFactory().create_options(
        current_zone=SafariZone.HERDING_GROUNDS,
        visited_zones=(),
        previous_option=None,
        random_source=FakeWeightedRandom(),  # type: ignore[arg-type]
    )

    assert {option.destination_zone for option in options} == {
        SafariZone.TALL_GRASS,
        SafariZone.HERDING_GROUNDS,
    }


def test_stay_is_not_guaranteed_when_random_source_selects_two_options():
    options = SafariRouteOptionFactory().create_options(
        current_zone=SafariZone.FOREST_ENTRANCE,
        visited_zones=(),
        previous_option=None,
        random_source=FakeWeightedRandom(option_count=2),  # type: ignore[arg-type]
    )

    assert len(options) == 2
    assert all(not option.stays_in_same_zone for option in options)


def test_stay_is_not_repeated_after_previous_stay():
    current_zone = SafariZone.MISTY_CLEARING
    options = SafariRouteOptionFactory().create_options(
        current_zone=current_zone,
        visited_zones=(current_zone,),
        previous_option=make_stay_option(current_zone),
        random_source=FakeWeightedRandom(),  # type: ignore[arg-type]
    )

    assert all(option.destination_zone != current_zone for option in options)


def test_recent_zone_remains_selectable_with_lower_weight():
    random_source = FakeWeightedRandom()
    options = SafariRouteOptionFactory().create_options(
        current_zone=SafariZone.FOREST_ENTRANCE,
        visited_zones=(SafariZone.DEEP_FOREST,),
        previous_option=None,
        random_source=random_source,  # type: ignore[arg-type]
    )

    assert options[0].destination_zone == SafariZone.DEEP_FOREST
    assert random_source.weight_calls[0][0] == 0.5
    assert random_source.weight_calls[0][1] == 1.0


def test_factory_uses_destination_affinities_events_and_deterministic_ids():
    options = SafariRouteOptionFactory().create_options(
        current_zone=SafariZone.RIVERBANK,
        visited_zones=(),
        previous_option=None,
        random_source=FakeWeightedRandom(),  # type: ignore[arg-type]
    )

    for option in options:
        destination = SAFARI_ZONE_DEFINITION_BY_ZONE[option.destination_zone]
        assert option.type_weight_modifiers == destination.base_type_weights
        assert option.allowed_events == destination.allowed_events
        assert SafariThematicEvent.NONE in option.allowed_events
        assert option.id == (
            f"{SafariZone.RIVERBANK.value}:{option.destination_zone.value}"
        )
        assert option.narrative_key == (
            f"riverbank_to_{option.destination_zone.value.lower()}"
        )


def test_fake_random_makes_weighted_selection_deterministic():
    options = SafariRouteOptionFactory().create_options(
        current_zone=SafariZone.FOREST_ENTRANCE,
        visited_zones=(),
        previous_option=None,
        random_source=FakeWeightedRandom(),  # type: ignore[arg-type]
    )

    assert [option.destination_zone for option in options] == [
        SafariZone.DEEP_FOREST,
        SafariZone.RIVERBANK,
        SafariZone.CLEARING,
    ]


def test_factory_reports_configuration_with_fewer_than_two_candidates():
    current_zone = SafariZone.HERDING_GROUNDS

    try:
        SafariRouteOptionFactory().create_options(
            current_zone=current_zone,
            visited_zones=(current_zone,),
            previous_option=make_stay_option(current_zone),
            random_source=FakeWeightedRandom(),  # type: ignore[arg-type]
        )
    except SafariRouteConfigurationError:
        pass
    else:
        raise AssertionError("Expected SafariRouteConfigurationError")
