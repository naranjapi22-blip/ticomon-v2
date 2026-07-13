import pytest

from core.safari import (
    SAFARI_ROUTE_SEGMENT_SCHEDULES,
    SafariRouteSchedulePolicy,
)


@pytest.mark.parametrize(
    ("total", "expected"),
    [
        (5, (1, 2, 2)),
        (7, (1, 3, 3)),
        (9, (1, 3, 2, 3)),
        (11, (1, 3, 3, 4)),
        (13, (1, 3, 3, 3, 3)),
    ],
)
def test_route_schedule_is_exact_positive_and_sums_to_total(total, expected):
    policy = SafariRouteSchedulePolicy()

    lengths = policy.segment_lengths_for(total)

    assert lengths == expected
    assert SAFARI_ROUTE_SEGMENT_SCHEDULES[total] == expected
    assert all(length > 0 for length in lengths)
    assert sum(lengths) == total


def test_route_schedule_rejects_unsupported_total():
    with pytest.raises(ValueError):
        SafariRouteSchedulePolicy().segment_lengths_for(6)


@pytest.mark.parametrize("index", [-1, 3])
def test_route_schedule_rejects_invalid_segment_index(index: int):
    with pytest.raises(ValueError):
        SafariRouteSchedulePolicy().segment_length_for(5, index)


def test_route_schedule_returns_segment_by_index():
    assert SafariRouteSchedulePolicy().segment_length_for(9, 2) == 2
