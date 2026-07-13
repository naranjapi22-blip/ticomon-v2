from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from core.safari import (
    SafariCaptureSelection,
    SafariPersistedCapture,
    SafariPersistedEncounterResult,
    SafariPersistedSlotResult,
    SafariSlotStatus,
)


def test_capture_selection_is_immutable_and_validates_values():
    selection = SafariCaptureSelection(1, uuid4(), 3)

    assert selection.trainer_id == 1
    assert selection.ball_count == 3
    assert not selection.is_confirmed
    with pytest.raises(FrozenInstanceError):
        selection.ball_count = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    ("trainer_id", "slot_id", "ball_count"),
    [(0, uuid4(), 1), (1, UUID(int=0), 1), (1, uuid4(), 0), (1, uuid4(), 4)],
)
def test_capture_selection_rejects_invalid_values(trainer_id, slot_id, ball_count):
    with pytest.raises(ValueError):
        SafariCaptureSelection(trainer_id, slot_id, ball_count)


def test_persisted_capture_rejects_empty_uuid_and_invalid_ids():
    with pytest.raises(ValueError):
        SafariPersistedCapture(1, UUID(int=0), 10)
    with pytest.raises(ValueError):
        SafariPersistedCapture(0, uuid4(), 10)
    with pytest.raises(ValueError):
        SafariPersistedCapture(1, uuid4(), 0)


def test_persisted_slot_result_explicitly_describes_captured_or_escaped():
    captured_slot_id = uuid4()
    capture = SafariPersistedCapture(1, captured_slot_id, 101)

    captured = SafariPersistedSlotResult(
        captured_slot_id,
        SafariSlotStatus.CAPTURED,
        capture,
    )
    escaped = SafariPersistedSlotResult(uuid4(), SafariSlotStatus.ESCAPED)

    assert captured.capture is capture
    assert escaped.capture is None


def test_persisted_slot_result_rejects_invalid_final_state():
    slot_id = uuid4()
    other_capture = SafariPersistedCapture(1, uuid4(), 101)

    with pytest.raises(ValueError):
        SafariPersistedSlotResult(UUID(int=0), SafariSlotStatus.ESCAPED)
    with pytest.raises(ValueError):
        SafariPersistedSlotResult(slot_id, SafariSlotStatus.AVAILABLE)
    with pytest.raises(ValueError):
        SafariPersistedSlotResult(slot_id, SafariSlotStatus.CAPTURED)
    with pytest.raises(ValueError):
        SafariPersistedSlotResult(
            slot_id,
            SafariSlotStatus.CAPTURED,
            other_capture,
        )
    with pytest.raises(ValueError):
        SafariPersistedSlotResult(
            slot_id,
            SafariSlotStatus.ESCAPED,
            SafariPersistedCapture(1, slot_id, 101),
        )


def test_persisted_encounter_result_copies_results_and_rejects_duplicates():
    slot_result = SafariPersistedSlotResult(uuid4(), SafariSlotStatus.ESCAPED)
    source = [slot_result]
    result = SafariPersistedEncounterResult(uuid4(), source)  # type: ignore[arg-type]
    source.clear()

    assert result.slot_results == (slot_result,)
    with pytest.raises(ValueError):
        SafariPersistedEncounterResult(UUID(int=0), ())
    with pytest.raises(ValueError):
        SafariPersistedEncounterResult(uuid4(), (slot_result, slot_result))


def test_persisted_capture_values_do_not_impose_trainer_uniqueness():
    first = SafariPersistedCapture(1, uuid4(), 101)
    second = SafariPersistedCapture(1, uuid4(), 102)

    assert first.trainer_id == second.trainer_id
