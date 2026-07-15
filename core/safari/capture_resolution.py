from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

from core.capture import CaptureAttemptService
from core.capture.domain.capture_ball import CaptureBall
from core.opportunity.opportunity import Opportunity
from core.safari.capture import SafariCaptureSelection, _require_non_empty_uuid
from core.safari.domain import (
    SafariCapturePolicy,
    SafariEncounterStatus,
    SafariSlotStatus,
)
from core.safari.encounter import SafariEncounter, SafariEncounterSlot


class SafariCaptureResolutionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SafariCaptureAttempt:
    trainer_id: int
    slot_id: UUID
    attempt_number: int
    success: bool
    chance: float
    roll: float
    failed_attempts_before: int
    failed_attempts_after: int
    capture_ball: CaptureBall

    def __post_init__(self) -> None:
        if self.trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")
        _require_non_empty_uuid(self.slot_id, "slot_id")
        if self.attempt_number <= 0:
            raise ValueError("attempt_number must be positive.")
        if self.failed_attempts_before < 0 or self.failed_attempts_after < 0:
            raise ValueError("failed attempt counts cannot be negative.")
        expected_after = self.failed_attempts_before + (0 if self.success else 1)
        if self.failed_attempts_after != expected_after:
            raise ValueError("failed attempt transition is inconsistent.")
        if not 0.0 <= self.chance <= 1.0:
            raise ValueError("chance must be between zero and one.")
        if not 0.0 <= self.roll <= 1.0:
            raise ValueError("roll must be between zero and one.")
        if self.capture_ball != CaptureBall.GREAT_BALL:
            raise ValueError("Safari capture attempts must use Great Ball mechanics.")


@dataclass(frozen=True, slots=True)
class SafariParticipantOutcome:
    trainer_id: int
    balls_committed: int
    attempts_executed: int
    balls_spent: int
    captured: bool
    final_opportunity: Opportunity | None = None

    def __post_init__(self) -> None:
        if self.trainer_id <= 0:
            raise ValueError("trainer_id must be positive.")
        if self.balls_committed <= 0:
            raise ValueError("balls_committed must be positive.")
        if self.attempts_executed < 0:
            raise ValueError("attempts_executed cannot be negative.")
        if self.balls_spent < 0 or self.balls_spent > self.balls_committed:
            raise ValueError("balls_spent must be between zero and balls_committed.")
        if self.attempts_executed > self.balls_committed:
            raise ValueError("attempts_executed cannot exceed balls_committed.")


@dataclass(frozen=True, slots=True)
class SafariSlotOutcome:
    slot_id: UUID
    status: SafariSlotStatus
    winner_trainer_id: int | None
    attempts: tuple[SafariCaptureAttempt, ...]
    balls_committed_by_trainer: Mapping[int, int]
    final_opportunity: Opportunity
    participant_outcomes: tuple[SafariParticipantOutcome, ...] = ()

    def __post_init__(self) -> None:
        _require_non_empty_uuid(self.slot_id, "slot_id")
        if self.status not in (SafariSlotStatus.CAPTURED, SafariSlotStatus.ESCAPED):
            raise ValueError("slot outcome status must be final.")
        participant_outcomes = tuple(self.participant_outcomes)
        captured_participant_ids = {
            item.trainer_id for item in participant_outcomes if item.captured
        }
        if self.status == SafariSlotStatus.CAPTURED:
            if participant_outcomes:
                if not captured_participant_ids:
                    raise ValueError("captured outcomes require a capture.")
                if (
                    self.winner_trainer_id is None
                    and len(captured_participant_ids) == 1
                ):
                    raise ValueError("captured outcomes require a winner.")
                if (
                    self.winner_trainer_id is not None
                    and self.winner_trainer_id not in captured_participant_ids
                ):
                    raise ValueError("winner must match a captured participant.")
            elif self.winner_trainer_id is None or self.winner_trainer_id <= 0:
                raise ValueError("captured outcomes require a winner.")
        elif self.winner_trainer_id is not None:
            raise ValueError("escaped outcomes cannot have a winner.")

        attempts = tuple(self.attempts)
        if any(attempt.slot_id != self.slot_id for attempt in attempts):
            raise ValueError("attempt slot IDs must match the outcome.")
        if tuple(attempt.attempt_number for attempt in attempts) != tuple(
            range(1, len(attempts) + 1)
        ):
            raise ValueError("attempt numbers must be sequential.")
        committed = dict(self.balls_committed_by_trainer)
        if any(trainer_id <= 0 for trainer_id in committed):
            raise ValueError("committed Ball trainer IDs must be positive.")
        if any(ball_count <= 0 for ball_count in committed.values()):
            raise ValueError("committed Ball counts must be positive.")
        if self.final_opportunity is None:
            raise ValueError("final_opportunity is required.")

        executed_by_trainer = Counter(attempt.trainer_id for attempt in attempts)
        if any(
            executed_count > committed.get(trainer_id, 0)
            for trainer_id, executed_count in executed_by_trainer.items()
        ):
            raise ValueError("executed attempts exceed committed Balls.")
        successful_attempts = [attempt for attempt in attempts if attempt.success]
        if participant_outcomes:
            if len(successful_attempts) != len(captured_participant_ids):
                raise ValueError("successful attempts must match participant captures.")
            if self.status == SafariSlotStatus.ESCAPED and successful_attempts:
                raise ValueError("escaped outcomes cannot contain successful attempts.")
            if (
                self.winner_trainer_id is not None
                and len(captured_participant_ids) == 1
                and successful_attempts[0].trainer_id != self.winner_trainer_id
            ):
                raise ValueError("winner must match the successful attempt.")
        elif self.status == SafariSlotStatus.CAPTURED:
            if len(successful_attempts) != 1 or not attempts[-1].success:
                raise ValueError(
                    "captured outcome requires one final successful attempt."
                )
            if successful_attempts[0].trainer_id != self.winner_trainer_id:
                raise ValueError("winner must match the successful attempt.")
        elif successful_attempts:
            raise ValueError("escaped outcomes cannot contain successful attempts.")

        if not participant_outcomes:
            participant_ids = sorted(set(committed) | set(executed_by_trainer))
            participant_outcomes = tuple(
                SafariParticipantOutcome(
                    trainer_id=trainer_id,
                    balls_committed=committed[trainer_id],
                    attempts_executed=executed_by_trainer.get(trainer_id, 0),
                    balls_spent=executed_by_trainer.get(trainer_id, 0),
                    captured=trainer_id == self.winner_trainer_id,
                    final_opportunity=(
                        self.final_opportunity
                        if trainer_id in executed_by_trainer
                        else None
                    ),
                )
                for trainer_id in participant_ids
            )
        participant_ids = [item.trainer_id for item in participant_outcomes]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("participant outcome trainer IDs must be unique.")

        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(
            self,
            "balls_committed_by_trainer",
            MappingProxyType(committed),
        )
        object.__setattr__(self, "participant_outcomes", participant_outcomes)

    @property
    def balls_committed(self) -> int:
        return sum(self.balls_committed_by_trainer.values())

    @property
    def attempts_executed(self) -> int:
        return len(self.attempts)


@dataclass(frozen=True, slots=True)
class SafariEncounterResolution:
    encounter_id: UUID
    slot_outcomes: tuple[SafariSlotOutcome, ...]

    def __post_init__(self) -> None:
        _require_non_empty_uuid(self.encounter_id, "encounter_id")
        outcomes = tuple(self.slot_outcomes)
        slot_ids = [outcome.slot_id for outcome in outcomes]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("slot outcome IDs must be unique.")
        object.__setattr__(self, "slot_outcomes", outcomes)

    @property
    def captured_slot_ids(self) -> tuple[UUID, ...]:
        return tuple(
            outcome.slot_id
            for outcome in self.slot_outcomes
            if outcome.status == SafariSlotStatus.CAPTURED
        )

    @property
    def escaped_slot_ids(self) -> tuple[UUID, ...]:
        return tuple(
            outcome.slot_id
            for outcome in self.slot_outcomes
            if outcome.status == SafariSlotStatus.ESCAPED
        )

    @property
    def winners_by_slot(self) -> Mapping[UUID, int]:
        return MappingProxyType(
            {
                outcome.slot_id: outcome.winner_trainer_id
                for outcome in self.slot_outcomes
                if outcome.winner_trainer_id is not None
            }
        )

    @property
    def balls_committed(self) -> int:
        return sum(outcome.balls_committed for outcome in self.slot_outcomes)

    @property
    def attempts_executed(self) -> int:
        return sum(outcome.attempts_executed for outcome in self.slot_outcomes)

    @property
    def balls_committed_by_trainer(self) -> Mapping[int, int]:
        totals: dict[int, int] = {}
        for outcome in self.slot_outcomes:
            for trainer_id, ball_count in outcome.balls_committed_by_trainer.items():
                totals[trainer_id] = totals.get(trainer_id, 0) + ball_count
        return MappingProxyType(totals)


class SafariCaptureResolver:
    def __init__(
        self,
        attempt_service: CaptureAttemptService,
        random_source: random.Random,
    ) -> None:
        self._attempt_service = attempt_service
        self._random_source = random_source

    def resolve(self, encounter: SafariEncounter) -> SafariEncounterResolution:
        if encounter.status != SafariEncounterStatus.RESOLVING:
            raise SafariCaptureResolutionError("Safari encounter must be resolving.")

        selections = tuple(encounter.selections_by_trainer.values())
        self._validate_selections(encounter, selections)
        selections_by_slot: dict[UUID, list[SafariCaptureSelection]] = {}
        for selection in selections:
            selections_by_slot.setdefault(selection.slot_id, []).append(selection)

        outcomes = tuple(
            (
                self._resolve_shared_slot(slot, selections_by_slot.get(slot.id, ()))
                if slot.capture_policy is SafariCapturePolicy.SHARED
                else self._resolve_slot(slot, selections_by_slot.get(slot.id, ()))
            )
            for slot in encounter.slots
        )
        return SafariEncounterResolution(encounter.id, outcomes)

    def _resolve_shared_slot(
        self,
        slot: SafariEncounterSlot,
        selections: tuple[SafariCaptureSelection, ...] | list[SafariCaptureSelection],
    ) -> SafariSlotOutcome:
        ordered_selections = sorted(selections, key=lambda item: item.trainer_id)
        committed = {
            selection.trainer_id: selection.ball_count
            for selection in ordered_selections
        }
        attempts: list[SafariCaptureAttempt] = []
        participant_outcomes: list[SafariParticipantOutcome] = []

        for selection in ordered_selections:
            opportunity = replace(slot.opportunity, failed_attempts=0)
            captured = False
            participant_attempts = 0

            for _ in range(selection.ball_count):
                participant_attempts += 1
                failed_attempts_before = opportunity.failed_attempts
                result = self._attempt_service.attempt(
                    opportunity,
                    CaptureBall.GREAT_BALL,
                    self._random_source,
                )
                opportunity = result.opportunity
                attempts.append(
                    SafariCaptureAttempt(
                        trainer_id=selection.trainer_id,
                        slot_id=slot.id,
                        attempt_number=len(attempts) + 1,
                        success=result.success,
                        chance=result.chance,
                        roll=result.roll,
                        failed_attempts_before=failed_attempts_before,
                        failed_attempts_after=opportunity.failed_attempts,
                        capture_ball=result.capture_ball,
                    )
                )
                if result.success:
                    captured = True
                    break

            participant_outcomes.append(
                SafariParticipantOutcome(
                    trainer_id=selection.trainer_id,
                    balls_committed=selection.ball_count,
                    attempts_executed=participant_attempts,
                    balls_spent=participant_attempts,
                    captured=captured,
                    final_opportunity=opportunity,
                )
            )

        captured_participants = [item for item in participant_outcomes if item.captured]
        return SafariSlotOutcome(
            slot_id=slot.id,
            status=(
                SafariSlotStatus.CAPTURED
                if captured_participants
                else SafariSlotStatus.ESCAPED
            ),
            winner_trainer_id=(
                captured_participants[0].trainer_id
                if len(captured_participants) == 1
                else None
            ),
            attempts=tuple(attempts),
            balls_committed_by_trainer=committed,
            final_opportunity=replace(slot.opportunity, failed_attempts=0),
            participant_outcomes=tuple(participant_outcomes),
        )

    def _resolve_slot(
        self,
        slot: SafariEncounterSlot,
        selections: tuple[SafariCaptureSelection, ...] | list[SafariCaptureSelection],
    ) -> SafariSlotOutcome:
        ordered_trainer_ids = [selection.trainer_id for selection in selections]
        self._random_source.shuffle(ordered_trainer_ids)
        selections_by_trainer = {
            selection.trainer_id: selection for selection in selections
        }
        ordered_selections = [
            selections_by_trainer[trainer_id] for trainer_id in ordered_trainer_ids
        ]
        committed = {
            selection.trainer_id: selection.ball_count
            for selection in ordered_selections
        }
        attempts: list[SafariCaptureAttempt] = []
        participant_outcomes: list[SafariParticipantOutcome] = []
        winner: int | None = None
        final_opportunity = replace(slot.opportunity, failed_attempts=0)

        for selection_index, selection in enumerate(ordered_selections):
            opportunity = replace(slot.opportunity, failed_attempts=0)
            participant_attempts = 0
            captured = False

            for _ in range(selection.ball_count):
                participant_attempts += 1
                failed_attempts_before = opportunity.failed_attempts
                result = self._attempt_service.attempt(
                    opportunity,
                    CaptureBall.GREAT_BALL,
                    self._random_source,
                )
                opportunity = result.opportunity
                attempts.append(
                    SafariCaptureAttempt(
                        trainer_id=selection.trainer_id,
                        slot_id=slot.id,
                        attempt_number=len(attempts) + 1,
                        success=result.success,
                        chance=result.chance,
                        roll=result.roll,
                        failed_attempts_before=failed_attempts_before,
                        failed_attempts_after=opportunity.failed_attempts,
                        capture_ball=result.capture_ball,
                    )
                )
                if result.success:
                    winner = selection.trainer_id
                    captured = True
                    final_opportunity = opportunity
                    break

            participant_outcomes.append(
                SafariParticipantOutcome(
                    trainer_id=selection.trainer_id,
                    balls_committed=selection.ball_count,
                    attempts_executed=participant_attempts,
                    balls_spent=participant_attempts,
                    captured=captured,
                    final_opportunity=opportunity,
                )
            )
            if captured:
                participant_outcomes.extend(
                    SafariParticipantOutcome(
                        trainer_id=unprocessed.trainer_id,
                        balls_committed=unprocessed.ball_count,
                        attempts_executed=0,
                        balls_spent=0,
                        captured=False,
                    )
                    for unprocessed in ordered_selections[selection_index + 1 :]
                )
                break

        return SafariSlotOutcome(
            slot_id=slot.id,
            status=(
                SafariSlotStatus.CAPTURED
                if winner is not None
                else SafariSlotStatus.ESCAPED
            ),
            winner_trainer_id=winner,
            attempts=tuple(attempts),
            balls_committed_by_trainer=committed,
            final_opportunity=final_opportunity,
            participant_outcomes=tuple(participant_outcomes),
        )

    @staticmethod
    def _validate_selections(
        encounter: SafariEncounter,
        selections: tuple[SafariCaptureSelection, ...],
    ) -> None:
        slot_ids = {slot.id for slot in encounter.slots}
        trainer_ids: set[int] = set()
        for selection in selections:
            if not selection.is_confirmed:
                raise SafariCaptureResolutionError(
                    "Safari capture selections must be confirmed."
                )
            if selection.slot_id not in slot_ids:
                raise SafariCaptureResolutionError(
                    "Safari capture selection references an unknown slot."
                )
            if selection.trainer_id in trainer_ids:
                raise SafariCaptureResolutionError(
                    "Safari participant has multiple capture selections."
                )
            trainer_ids.add(selection.trainer_id)
