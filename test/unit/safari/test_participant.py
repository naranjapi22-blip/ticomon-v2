import pytest

from core.safari import NotEnoughSafariBalls, SafariParticipant


def test_participant_valid_construction_and_properties():
    participant = SafariParticipant(
        trainer_id=10,
        initial_balls=9,
        remaining_balls=7,
        captured_creature_ids=[101, 102],
    )

    assert participant.trainer_id == 10
    assert participant.initial_balls == 9
    assert participant.remaining_balls == 7
    assert participant.balls_spent == 2
    assert participant.capture_count == 2
    assert participant.can_capture
    assert participant.captured_creature_ids == (101, 102)


@pytest.mark.parametrize(
    ("trainer_id", "initial_balls", "remaining_balls"),
    [(0, 9, 9), (1, 0, 0), (1, 9, -1), (1, 9, 10)],
)
def test_participant_rejects_invalid_state(
    trainer_id: int,
    initial_balls: int,
    remaining_balls: int,
):
    with pytest.raises(ValueError):
        SafariParticipant(
            trainer_id=trainer_id,
            initial_balls=initial_balls,
            remaining_balls=remaining_balls,
        )

    with pytest.raises(ValueError):
        SafariParticipant(
            trainer_id=1,
            initial_balls=9,
            remaining_balls=9,
            captured_creature_ids=[0],
        )


@pytest.mark.parametrize("amount", [1, 2, 3])
def test_spend_balls_accepts_one_to_three(amount: int):
    participant = SafariParticipant(1, 9, 9)

    participant.spend_balls(amount)

    assert participant.remaining_balls == 9 - amount
    assert participant.balls_spent == amount


@pytest.mark.parametrize("amount", [0, 4])
def test_spend_balls_rejects_invalid_amount(amount: int):
    participant = SafariParticipant(1, 9, 9)

    with pytest.raises(ValueError):
        participant.spend_balls(amount)


def test_spend_balls_rejects_amount_above_balance():
    participant = SafariParticipant(1, 9, 2)

    with pytest.raises(NotEnoughSafariBalls):
        participant.spend_balls(3)


def test_can_capture_is_false_without_remaining_balls():
    participant = SafariParticipant(1, 9, 0)

    assert not participant.can_capture
    assert participant.balls_spent == 9


def test_record_capture_preserves_order_and_exposes_immutable_tuple():
    participant = SafariParticipant(1, 9, 9)

    participant.record_capture(20)
    participant.record_capture(10)

    captures = participant.captured_creature_ids
    assert captures == (20, 10)
    assert participant.capture_count == 2
    assert isinstance(captures, tuple)

    with pytest.raises(ValueError):
        participant.record_capture(0)
