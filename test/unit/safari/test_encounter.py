from uuid import UUID, uuid4

import pytest

from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SafariCaptureSelection,
    SafariComposition,
    SafariEncounter,
    SafariEncounterClosed,
    SafariEncounterSlot,
    SafariEncounterStatus,
    SafariPersistedCapture,
    SafariPersistedEncounterResult,
    SafariPersistedSlotResult,
    SafariSelectionAlreadyConfirmed,
    SafariSlotStatus,
)
from test.factories import create_species


def make_slot(species_id: int = 25) -> SafariEncounterSlot:
    return SafariEncounterSlot(
        uuid4(),
        OpportunityFactory.create(create_species(id=species_id)),
    )


def make_encounter(slot_count: int = 1) -> SafariEncounter:
    return SafariEncounter(
        uuid4(),
        SafariComposition.NORMAL,
        tuple(make_slot(index + 1) for index in range(slot_count)),
    )


def test_slot_exposes_opportunity_and_rejects_empty_identity():
    slot = make_slot()

    assert slot.species_id == slot.opportunity.species.id
    assert slot.status == SafariSlotStatus.AVAILABLE
    with pytest.raises(ValueError):
        SafariEncounterSlot(UUID(int=0), slot.opportunity)
    with pytest.raises(ValueError):
        SafariEncounterSlot(uuid4(), None)  # type: ignore[arg-type]


def test_encounter_requires_identity_and_unique_nonempty_slots():
    slot = make_slot()

    with pytest.raises(ValueError):
        SafariEncounter(UUID(int=0), SafariComposition.NORMAL, (slot,))
    with pytest.raises(ValueError):
        SafariEncounter(uuid4(), SafariComposition.NORMAL, ())
    with pytest.raises(ValueError):
        SafariEncounter(uuid4(), SafariComposition.NORMAL, (slot, slot))


def test_encounter_freezes_eligibility_and_exposes_immutable_collections():
    encounter = make_encounter()
    eligible = frozenset({1, 2})

    encounter._set_eligible_participant_ids(eligible)

    assert encounter.eligible_participant_ids == eligible
    assert isinstance(encounter.slots, tuple)
    with pytest.raises(ValueError):
        encounter._set_eligible_participant_ids(frozenset({1}))
    with pytest.raises(TypeError):
        encounter.selections_by_trainer[1] = SafariCaptureSelection(  # type: ignore[index]
            1, encounter.slots[0].id, 1
        )


def test_pending_selection_can_be_replaced_without_confirmation():
    encounter = make_encounter(2)
    encounter._set_eligible_participant_ids(frozenset({1}))

    encounter._set_selection(SafariCaptureSelection(1, encounter.slots[0].id, 1))
    encounter._set_selection(SafariCaptureSelection(1, encounter.slots[1].id, 2))

    assert encounter.selection_for(1).slot_id == encounter.slots[1].id
    assert encounter.selection_for(1).ball_count == 2


def test_confirmed_selection_is_closed_and_only_counted_once():
    encounter = make_encounter()
    encounter._set_eligible_participant_ids(frozenset({1}))
    encounter._set_selection(SafariCaptureSelection(1, encounter.slots[0].id, 1))

    confirmed = encounter._confirm_selection(1)

    assert confirmed.is_confirmed
    assert encounter.all_eligible_participants_decided
    with pytest.raises(SafariSelectionAlreadyConfirmed):
        encounter._confirm_selection(1)
    with pytest.raises(SafariSelectionAlreadyConfirmed):
        encounter._set_selection(SafariCaptureSelection(1, encounter.slots[0].id, 2))


def test_decline_is_a_decision_and_cannot_replace_confirmation():
    encounter = make_encounter()
    encounter._set_eligible_participant_ids(frozenset({1, 2}))
    encounter._set_selection(SafariCaptureSelection(1, encounter.slots[0].id, 1))
    encounter._confirm_selection(1)

    encounter._decline(2)

    assert encounter.declined_participant_ids == frozenset({2})
    assert encounter.all_eligible_participants_decided
    with pytest.raises(SafariSelectionAlreadyConfirmed):
        encounter._decline(1)


def test_only_eligible_participants_can_select_or_decline():
    encounter = make_encounter()
    encounter._set_eligible_participant_ids(frozenset({1}))

    with pytest.raises(ValueError):
        encounter._set_selection(SafariCaptureSelection(2, encounter.slots[0].id, 1))
    with pytest.raises(ValueError):
        encounter._decline(2)


def test_resolution_applies_explicit_result_for_every_slot():
    encounter = make_encounter(2)
    first, second = encounter.slots
    encounter._set_eligible_participant_ids(frozenset({1}))
    encounter._set_selection(SafariCaptureSelection(1, first.id, 1))
    encounter._confirm_selection(1)
    encounter._begin_resolution()
    result = SafariPersistedEncounterResult(
        encounter.id,
        (
            SafariPersistedSlotResult(
                first.id,
                SafariSlotStatus.CAPTURED,
                SafariPersistedCapture(1, first.id, 101),
            ),
            SafariPersistedSlotResult(second.id, SafariSlotStatus.ESCAPED),
        ),
    )

    encounter._apply_persisted_result(result)

    assert encounter.status == SafariEncounterStatus.RESOLVED
    assert first.status == SafariSlotStatus.CAPTURED
    assert second.status == SafariSlotStatus.ESCAPED
    with pytest.raises(SafariEncounterClosed):
        encounter._decline(1)
