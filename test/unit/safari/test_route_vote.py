from datetime import datetime
from types import MappingProxyType

import pytest

from core.safari import (
    SafariRouteOption,
    SafariRouteVote,
    SafariRouteVoteClosed,
    SafariRouteVoteStatus,
    SafariThematicEvent,
    SafariZone,
)


class FakeRandom:
    def __init__(self, selected_index: int) -> None:
        self._selected_index = selected_index

    def choice(self, candidates):
        return candidates[self._selected_index]


def make_option(
    destination: SafariZone,
    source: SafariZone = SafariZone.FOREST_ENTRANCE,
    option_id: str | None = None,
) -> SafariRouteOption:
    return SafariRouteOption(
        id=option_id or f"{source.value}:{destination.value}",
        source_zone=source,
        destination_zone=destination,
        type_weight_modifiers={"grass": 1.5},
        allowed_events=(SafariThematicEvent.NONE,),
        narrative_key=f"{source.value.lower()}_to_{destination.value.lower()}",
    )


def make_vote() -> SafariRouteVote:
    return SafariRouteVote(
        options=(
            make_option(SafariZone.DEEP_FOREST),
            make_option(SafariZone.RIVERBANK),
            make_option(SafariZone.CLEARING),
        ),
        opened_at=datetime(2026, 7, 12, 10, 0),
    )


@pytest.mark.parametrize("option_count", [1, 4])
def test_vote_requires_between_two_and_three_options(option_count: int):
    options = (
        make_option(destination)
        for destination in (
            SafariZone.DEEP_FOREST,
            SafariZone.RIVERBANK,
            SafariZone.CLEARING,
            SafariZone.FOREST_ENTRANCE,
        )[:option_count]
    )

    with pytest.raises(ValueError):
        SafariRouteVote(
            options=tuple(options),
            opened_at=datetime(2026, 7, 12, 10, 0),
        )


def test_vote_requires_unique_option_ids_and_shared_source():
    duplicate_id = "duplicate"
    with pytest.raises(ValueError):
        SafariRouteVote(
            options=(
                make_option(SafariZone.DEEP_FOREST, option_id=duplicate_id),
                make_option(SafariZone.RIVERBANK, option_id=duplicate_id),
            ),
            opened_at=datetime(2026, 7, 12, 10, 0),
        )

    with pytest.raises(ValueError):
        SafariRouteVote(
            options=(
                make_option(SafariZone.DEEP_FOREST),
                make_option(
                    SafariZone.DEEP_FOREST,
                    source=SafariZone.RIVERBANK,
                ),
            ),
            opened_at=datetime(2026, 7, 12, 10, 0),
        )


def test_participant_can_vote_and_replace_previous_vote():
    vote = make_vote()
    first_id = vote.options[0].id
    second_id = vote.options[1].id

    vote.cast_vote(10, first_id, participant_ids={10, 20})
    vote.cast_vote(10, second_id, participant_ids={10, 20})

    assert dict(vote.votes_by_trainer) == {10: second_id}
    assert isinstance(vote.votes_by_trainer, MappingProxyType)


def test_vote_rejects_non_participant_and_unknown_option():
    vote = make_vote()

    with pytest.raises(ValueError):
        vote.cast_vote(30, vote.options[0].id, participant_ids={10, 20})

    with pytest.raises(ValueError):
        vote.cast_vote(10, "unknown", participant_ids={10, 20})


def test_simple_majority_resolves_and_includes_zero_counts():
    vote = make_vote()
    selected = vote.options[0]
    vote.cast_vote(10, selected.id, participant_ids={10, 20, 30})
    vote.cast_vote(20, selected.id, participant_ids={10, 20, 30})
    vote.cast_vote(30, vote.options[1].id, participant_ids={10, 20, 30})

    result = vote.resolve(FakeRandom(0))  # type: ignore[arg-type]

    assert result.selected_option is selected
    assert result.vote_counts == {
        vote.options[0].id: 2,
        vote.options[1].id: 1,
        vote.options[2].id: 0,
    }
    assert isinstance(result.vote_counts, MappingProxyType)
    assert not result.was_tiebreak
    assert not result.was_random_due_to_no_votes
    assert vote.status == SafariRouteVoteStatus.RESOLVED


def test_tie_uses_controlled_random_source():
    vote = make_vote()
    vote.cast_vote(10, vote.options[0].id, participant_ids={10, 20})
    vote.cast_vote(20, vote.options[1].id, participant_ids={10, 20})

    result = vote.resolve(FakeRandom(1))  # type: ignore[arg-type]

    assert result.selected_option is vote.options[1]
    assert result.was_tiebreak
    assert not result.was_random_due_to_no_votes


def test_no_votes_selects_randomly_without_marking_tiebreak():
    vote = make_vote()

    result = vote.resolve(FakeRandom(2))  # type: ignore[arg-type]

    assert result.selected_option is vote.options[2]
    assert result.vote_counts == {option.id: 0 for option in vote.options}
    assert result.was_random_due_to_no_votes
    assert not result.was_tiebreak


def test_vote_cannot_resolve_twice():
    vote = make_vote()
    vote.resolve(FakeRandom(0))  # type: ignore[arg-type]

    with pytest.raises(SafariRouteVoteClosed):
        vote.resolve(FakeRandom(0))  # type: ignore[arg-type]


def test_cancel_is_idempotent_and_cancelled_vote_is_closed():
    vote = make_vote()
    vote.cancel()
    vote.cancel()

    assert vote.status == SafariRouteVoteStatus.CANCELLED

    with pytest.raises(SafariRouteVoteClosed):
        vote.cast_vote(10, vote.options[0].id, participant_ids={10})

    with pytest.raises(SafariRouteVoteClosed):
        vote.resolve(FakeRandom(0))  # type: ignore[arg-type]


def test_resolved_vote_cannot_be_cancelled():
    vote = make_vote()
    vote.resolve(FakeRandom(0))  # type: ignore[arg-type]

    with pytest.raises(SafariRouteVoteClosed):
        vote.cancel()
