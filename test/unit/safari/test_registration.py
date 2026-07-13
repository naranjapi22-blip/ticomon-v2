from datetime import datetime

import pytest

from core.safari import (
    SafariParticipantLimitReached,
    SafariRegistration,
    SafariRegistrationClosed,
    SafariRegistrationStatus,
)

OPENED_AT = datetime(2026, 7, 12, 10, 0)


def make_registration(
    participant_ids: set[int] | None = None,
) -> SafariRegistration:
    return SafariRegistration(
        guild_id=123,
        participant_ids=participant_ids or set(),
        opened_at=OPENED_AT,
    )


def test_registration_can_be_created_and_deduplicates_participants():
    registration = SafariRegistration(
        guild_id=123,
        participant_ids=[10, 10, 20],
        opened_at=OPENED_AT,
    )

    assert registration.guild_id == 123
    assert registration.opened_at == OPENED_AT
    assert registration.status == SafariRegistrationStatus.OPEN
    assert registration.participant_ids == frozenset({10, 20})
    assert registration.participant_count == 2
    assert not registration.is_empty


def test_registration_rejects_invalid_construction_values():
    with pytest.raises(ValueError):
        SafariRegistration(
            guild_id=0,
            participant_ids=set(),
            opened_at=OPENED_AT,
        )

    with pytest.raises(ValueError):
        SafariRegistration(
            guild_id=123,
            participant_ids=set(),
            opened_at=None,  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError):
        SafariRegistration(
            guild_id=123,
            participant_ids={0},
            opened_at=OPENED_AT,
        )


def test_join_adds_participant_and_is_idempotent():
    registration = make_registration()

    registration.join(10, maximum_participants=2)
    registration.join(10, maximum_participants=2)

    assert registration.participant_ids == frozenset({10})
    assert registration.participant_count == 1


def test_join_validates_limit_and_participant_id():
    registration = make_registration({10})

    with pytest.raises(ValueError):
        registration.join(20, maximum_participants=0)

    with pytest.raises(ValueError):
        registration.join(0, maximum_participants=2)

    with pytest.raises(SafariParticipantLimitReached):
        registration.join(20, maximum_participants=1)


@pytest.mark.parametrize(
    "terminal_action",
    [SafariRegistration.cancel, SafariRegistration.consume],
)
def test_join_is_rejected_after_registration_closes(terminal_action):
    registration = make_registration()
    terminal_action(registration)

    with pytest.raises(SafariRegistrationClosed):
        registration.join(10, maximum_participants=2)


def test_leave_removes_existing_participant_and_is_idempotent():
    registration = make_registration({10})

    assert registration.leave(10)
    assert not registration.leave(10)
    assert registration.is_empty
    assert registration.participant_count == 0


@pytest.mark.parametrize(
    "terminal_action",
    [SafariRegistration.cancel, SafariRegistration.consume],
)
def test_leave_is_rejected_after_registration_closes(terminal_action):
    registration = make_registration({10})
    terminal_action(registration)

    with pytest.raises(SafariRegistrationClosed):
        registration.leave(10)


def test_cancel_is_idempotent_but_consumed_registration_cannot_cancel():
    registration = make_registration()

    registration.cancel()
    registration.cancel()

    assert registration.status == SafariRegistrationStatus.CANCELLED

    consumed = make_registration()
    consumed.consume()

    with pytest.raises(SafariRegistrationClosed):
        consumed.cancel()


def test_consume_is_idempotent_but_cancelled_registration_cannot_consume():
    registration = make_registration()

    registration.consume()
    registration.consume()

    assert registration.status == SafariRegistrationStatus.CONSUMED

    cancelled = make_registration()
    cancelled.cancel()

    with pytest.raises(SafariRegistrationClosed):
        cancelled.consume()


def test_has_minimum_reports_participant_threshold_and_validates_input():
    registration = make_registration({10})

    assert not registration.has_minimum(2)

    registration.join(20, maximum_participants=2)

    assert registration.has_minimum(2)

    with pytest.raises(ValueError):
        registration.has_minimum(0)


def test_empty_registration_properties():
    registration = make_registration()

    assert registration.is_empty
    assert registration.participant_count == 0
