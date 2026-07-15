from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from core.safari.domain import SafariSlotStatus


def _require_non_empty_uuid(value: UUID, field_name: str) -> None:
    if not isinstance(value, UUID) or value.int == 0:
        raise ValueError(f"{field_name} must be a non-empty UUID.")


@dataclass(frozen=True, slots=True)
class SafariCaptureSelection:
    trainer_id: int
    slot_id: UUID
    ball_count: int
    is_confirmed: bool = False

    def __post_init__(self) -> None:
        if self.trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")
        _require_non_empty_uuid(self.slot_id, "slot_id")
        if self.ball_count < 1 or self.ball_count > 3:
            raise ValueError("ball_count must be between 1 and 3.")


@dataclass(frozen=True, slots=True)
class SafariPersistedCapture:
    trainer_id: int
    slot_id: UUID
    creature_id: int

    def __post_init__(self) -> None:
        if self.trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")
        _require_non_empty_uuid(self.slot_id, "slot_id")
        if self.creature_id <= 0:
            raise ValueError("creature_id must be positive.")


@dataclass(frozen=True, slots=True)
class SafariPersistedSlotResult:
    slot_id: UUID
    status: SafariSlotStatus
    capture: SafariPersistedCapture | None = None
    captures: tuple[SafariPersistedCapture, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_uuid(self.slot_id, "slot_id")
        captures = tuple(self.captures)
        if self.capture is not None:
            if captures and self.capture not in captures:
                raise ValueError("capture must be included in captures.")
            if not captures:
                captures = (self.capture,)

        if any(capture.slot_id != self.slot_id for capture in captures):
            raise ValueError("capture slot_ids must match the slot result.")

        if self.status == SafariSlotStatus.CAPTURED:
            if not captures:
                raise ValueError("captured slot results require a capture.")
            object.__setattr__(self, "captures", captures)
            return

        if self.status == SafariSlotStatus.ESCAPED:
            if captures:
                raise ValueError("escaped slot results cannot contain a capture.")
            object.__setattr__(self, "captures", captures)
            return

        raise ValueError("persisted slot result must be final.")


@dataclass(frozen=True, slots=True)
class SafariPersistedEncounterResult:
    encounter_id: UUID
    slot_results: tuple[SafariPersistedSlotResult, ...]

    def __post_init__(self) -> None:
        _require_non_empty_uuid(self.encounter_id, "encounter_id")
        copied_results = tuple(self.slot_results)
        slot_ids = [result.slot_id for result in copied_results]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("persisted slot result IDs must be unique.")

        object.__setattr__(self, "slot_results", copied_results)
