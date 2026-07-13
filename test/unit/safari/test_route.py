from types import MappingProxyType

import pytest

from core.safari import (
    SafariRouteOption,
    SafariRouteSegment,
    SafariThematicEvent,
    SafariZone,
)


def make_option() -> SafariRouteOption:
    return SafariRouteOption(
        id="FOREST_ENTRANCE:RIVERBANK",
        source_zone=SafariZone.FOREST_ENTRANCE,
        destination_zone=SafariZone.RIVERBANK,
        type_weight_modifiers={"water": 1.5},
        allowed_events=(SafariThematicEvent.NONE, SafariThematicEvent.FISHING),
        narrative_key="forest_entrance_to_riverbank",
    )


def test_route_option_is_valid_and_immutable():
    weights = {"water": 1.5}
    option = SafariRouteOption(
        id="FOREST_ENTRANCE:RIVERBANK",
        source_zone=SafariZone.FOREST_ENTRANCE,
        destination_zone=SafariZone.RIVERBANK,
        type_weight_modifiers=weights,
        allowed_events=(SafariThematicEvent.NONE,),
        narrative_key="forest_entrance_to_riverbank",
    )
    weights["water"] = 9.0

    assert option.type_weight_modifiers["water"] == 1.5
    assert isinstance(option.type_weight_modifiers, MappingProxyType)
    assert not option.stays_in_same_zone

    with pytest.raises(TypeError):
        option.type_weight_modifiers["water"] = 2.0  # type: ignore[index]


@pytest.mark.parametrize(
    ("weights", "events"),
    [
        ({"Water": 1.5}, (SafariThematicEvent.NONE,)),
        ({"water": 0.0}, (SafariThematicEvent.NONE,)),
        ({"water": 1.5}, (SafariThematicEvent.FISHING,)),
    ],
)
def test_route_option_rejects_invalid_weights_or_events(weights, events):
    with pytest.raises(ValueError):
        SafariRouteOption(
            id="FOREST_ENTRANCE:RIVERBANK",
            source_zone=SafariZone.FOREST_ENTRANCE,
            destination_zone=SafariZone.RIVERBANK,
            type_weight_modifiers=weights,
            allowed_events=events,
            narrative_key="forest_entrance_to_riverbank",
        )


def test_route_option_reports_stay_in_same_zone():
    option = SafariRouteOption(
        id="RIVERBANK:RIVERBANK",
        source_zone=SafariZone.RIVERBANK,
        destination_zone=SafariZone.RIVERBANK,
        type_weight_modifiers={"water": 1.5},
        allowed_events=(SafariThematicEvent.NONE,),
        narrative_key="riverbank_to_riverbank",
    )

    assert option.stays_in_same_zone


def test_route_segment_completes_without_going_below_zero():
    segment = SafariRouteSegment(
        zone=SafariZone.RIVERBANK,
        remaining_encounters=1,
        type_weight_modifiers={"water": 1.5},
        allowed_events=(SafariThematicEvent.NONE,),
        source_option_id=make_option().id,
    )

    assert not segment.is_complete
    segment.complete_encounter()
    assert segment.is_complete
    assert segment.remaining_encounters == 0

    with pytest.raises(ValueError):
        segment.complete_encounter()


def test_route_segment_validates_duration_weights_and_events():
    with pytest.raises(ValueError):
        SafariRouteSegment(
            zone=SafariZone.RIVERBANK,
            remaining_encounters=0,
            type_weight_modifiers={"water": 1.5},
            allowed_events=(SafariThematicEvent.NONE,),
        )

    with pytest.raises(ValueError):
        SafariRouteSegment(
            zone=SafariZone.RIVERBANK,
            remaining_encounters=1,
            type_weight_modifiers={"water": -1.0},
            allowed_events=(SafariThematicEvent.NONE,),
        )

    with pytest.raises(ValueError):
        SafariRouteSegment(
            zone=SafariZone.RIVERBANK,
            remaining_encounters=1,
            type_weight_modifiers={"water": 1.5},
            allowed_events=(SafariThematicEvent.FISHING,),
        )


def test_route_segment_freezes_weights_and_events():
    weights = {"water": 1.5}
    events = [SafariThematicEvent.NONE]
    segment = SafariRouteSegment(
        zone=SafariZone.RIVERBANK,
        remaining_encounters=2,
        type_weight_modifiers=weights,
        allowed_events=events,  # type: ignore[arg-type]
    )
    weights["water"] = 4.0
    events.append(SafariThematicEvent.FISHING)

    assert segment.type_weight_modifiers["water"] == 1.5
    assert segment.allowed_events == (SafariThematicEvent.NONE,)
    assert isinstance(segment.type_weight_modifiers, MappingProxyType)
