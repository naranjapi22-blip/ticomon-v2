from __future__ import annotations

from types import MappingProxyType
from typing import Collection, Mapping
from uuid import UUID

from core.opportunity.opportunity import Opportunity
from core.safari.capture import (
    SafariCaptureSelection,
    SafariPersistedEncounterResult,
    _require_non_empty_uuid,
)
from core.safari.domain import (
    SafariComposition,
    SafariEncounterStatus,
    SafariSlotStatus,
    SafariThematicEvent,
)


class SafariEncounterClosed(ValueError):
    pass


class SafariSelectionAlreadyConfirmed(ValueError):
    pass


class SafariEncounterSlot:
    def __init__(
        self,
        id: UUID,
        opportunity: Opportunity,
    ) -> None:
        _require_non_empty_uuid(id, "id")
        if opportunity is None:
            raise ValueError("opportunity is required.")

        self._id = id
        self._opportunity = opportunity
        self._status = SafariSlotStatus.AVAILABLE

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def opportunity(self) -> Opportunity:
        return self._opportunity

    @property
    def species_id(self) -> int:
        return self._opportunity.species.id

    @property
    def status(self) -> SafariSlotStatus:
        return self._status

    def _mark_captured(self) -> None:
        self._set_final_status(SafariSlotStatus.CAPTURED)

    def _mark_escaped(self) -> None:
        self._set_final_status(SafariSlotStatus.ESCAPED)

    def _set_final_status(self, status: SafariSlotStatus) -> None:
        if self._status != SafariSlotStatus.AVAILABLE:
            raise SafariEncounterClosed("Safari encounter slot is already final.")
        self._status = status


class SafariEncounter:
    def __init__(
        self,
        id: UUID,
        composition: SafariComposition,
        slots: Collection[SafariEncounterSlot],
        is_regional_herd: bool = False,
        event: SafariThematicEvent = SafariThematicEvent.NONE,
    ) -> None:
        _require_non_empty_uuid(id, "id")
        copied_slots = tuple(slots)
        if not copied_slots:
            raise ValueError("Safari encounter requires at least one slot.")

        slot_ids = [slot.id for slot in copied_slots]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("Safari encounter slot IDs must be unique.")

        self._id = id
        self._composition = composition
        self._slots = copied_slots
        self._slot_by_id = {slot.id: slot for slot in copied_slots}
        self._is_regional_herd = is_regional_herd
        self._event = event
        self._eligible_participant_ids: frozenset[int] | None = None
        self._selections_by_trainer: dict[int, SafariCaptureSelection] = {}
        self._declined_participant_ids: set[int] = set()
        self._status = SafariEncounterStatus.OPEN

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def composition(self) -> SafariComposition:
        return self._composition

    @property
    def slots(self) -> tuple[SafariEncounterSlot, ...]:
        return self._slots

    @property
    def is_regional_herd(self) -> bool:
        return self._is_regional_herd

    @property
    def event(self) -> SafariThematicEvent:
        return self._event

    @property
    def eligible_participant_ids(self) -> frozenset[int]:
        return self._eligible_participant_ids or frozenset()

    @property
    def selections_by_trainer(self) -> Mapping[int, SafariCaptureSelection]:
        return MappingProxyType(dict(self._selections_by_trainer))

    @property
    def declined_participant_ids(self) -> frozenset[int]:
        return frozenset(self._declined_participant_ids)

    @property
    def status(self) -> SafariEncounterStatus:
        return self._status

    @property
    def all_eligible_participants_decided(self) -> bool:
        if self._eligible_participant_ids is None:
            return False
        confirmed_ids = {
            trainer_id
            for trainer_id, selection in self._selections_by_trainer.items()
            if selection.is_confirmed
        }
        return (
            confirmed_ids | self._declined_participant_ids
            == self._eligible_participant_ids
        )

    def selection_for(self, trainer_id: int) -> SafariCaptureSelection | None:
        return self._selections_by_trainer.get(trainer_id)

    def _set_eligible_participant_ids(
        self,
        participant_ids: frozenset[int],
    ) -> None:
        self._assert_open()
        if self._eligible_participant_ids is not None:
            raise ValueError("eligible participants are already set.")
        if any(trainer_id <= 0 for trainer_id in participant_ids):
            raise ValueError("eligible participant IDs must be positive.")
        self._eligible_participant_ids = frozenset(participant_ids)

    def _set_selection(self, selection: SafariCaptureSelection) -> None:
        self._assert_open()
        self._assert_eligible(selection.trainer_id)
        if selection.slot_id not in self._slot_by_id:
            raise ValueError("unknown Safari encounter slot.")
        if self._slot_by_id[selection.slot_id].status != SafariSlotStatus.AVAILABLE:
            raise ValueError("Safari encounter slot is not available.")
        if selection.trainer_id in self._declined_participant_ids:
            raise ValueError("participant already declined this encounter.")

        current = self._selections_by_trainer.get(selection.trainer_id)
        if current is not None and current.is_confirmed:
            raise SafariSelectionAlreadyConfirmed(
                "Safari capture selection is already confirmed."
            )
        self._selections_by_trainer[selection.trainer_id] = selection

    def _confirm_selection(self, trainer_id: int) -> SafariCaptureSelection:
        self._assert_open()
        self._assert_eligible(trainer_id)
        selection = self._selections_by_trainer.get(trainer_id)
        if selection is None:
            raise ValueError("participant has no Safari capture selection.")
        if selection.is_confirmed:
            raise SafariSelectionAlreadyConfirmed(
                "Safari capture selection is already confirmed."
            )

        confirmed = SafariCaptureSelection(
            trainer_id=selection.trainer_id,
            slot_id=selection.slot_id,
            ball_count=selection.ball_count,
            is_confirmed=True,
        )
        self._selections_by_trainer[trainer_id] = confirmed
        return confirmed

    def _decline(self, trainer_id: int) -> None:
        self._assert_open()
        self._assert_eligible(trainer_id)
        selection = self._selections_by_trainer.get(trainer_id)
        if selection is not None and selection.is_confirmed:
            raise SafariSelectionAlreadyConfirmed(
                "confirmed selection cannot be declined."
            )
        self._selections_by_trainer.pop(trainer_id, None)
        self._declined_participant_ids.add(trainer_id)

    def _begin_resolution(self) -> None:
        self._assert_open()
        if not self.all_eligible_participants_decided:
            raise ValueError("not all eligible participants have decided.")
        self._status = SafariEncounterStatus.RESOLVING

    def _apply_persisted_result(
        self,
        result: SafariPersistedEncounterResult,
    ) -> None:
        for slot_result in result.slot_results:
            slot = self._slot_by_id[slot_result.slot_id]
            if slot_result.status == SafariSlotStatus.CAPTURED:
                slot._mark_captured()
            else:
                slot._mark_escaped()
        self._status = SafariEncounterStatus.RESOLVED

    def _assert_eligible(self, trainer_id: int) -> None:
        if (
            self._eligible_participant_ids is None
            or trainer_id not in self._eligible_participant_ids
        ):
            raise ValueError("trainer is not eligible for this encounter.")

    def _assert_open(self) -> None:
        if self._status != SafariEncounterStatus.OPEN:
            raise SafariEncounterClosed("Safari encounter is closed.")
