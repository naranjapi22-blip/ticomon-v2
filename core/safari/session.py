from __future__ import annotations

import random
from datetime import datetime
from types import MappingProxyType
from typing import Collection, Mapping
from uuid import UUID

from core.safari.capture import (
    SafariCaptureSelection,
    SafariPersistedEncounterResult,
    _require_non_empty_uuid,
)
from core.safari.domain import (
    SAFARI_LEVEL_CONFIGS,
    SAFARI_VALID_WEATHER_BY_MAP,
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariEncounterStatus,
    SafariExtraordinaryFlags,
    SafariFinishReason,
    SafariMap,
    SafariPhase,
    SafariSessionStatus,
    SafariSlotStatus,
    SafariTimeOfDay,
    SafariWeather,
)
from core.safari.encounter import (
    SafariEncounter,
    SafariSelectionAlreadyConfirmed,
)
from core.safari.history import (
    SafariEncounterHistoryEntry,
    SafariRouteProgressEntry,
)
from core.safari.participant import SafariParticipant
from core.safari.route import SafariRouteSegment
from core.safari.route_schedule import SafariRouteSchedulePolicy
from core.safari.route_vote import SafariRouteVote, SafariRouteVoteResult


class SafariSessionClosed(ValueError):
    pass


class SafariInvalidSessionState(ValueError):
    pass


class SafariSession:
    def __init__(
        self,
        id: UUID,
        guild_id: int,
        participants: Collection[SafariParticipant],
        total_encounters: int,
        initial_segment: SafariRouteSegment,
        started_at: datetime,
        unlock_id: int,
        level: int,
        safari_map: SafariMap,
        weather: SafariWeather,
        time_of_day: SafariTimeOfDay,
    ) -> None:
        _require_non_empty_uuid(id, "id")
        if guild_id <= 0:
            raise ValueError("guild_id must be positive.")
        if started_at is None:
            raise ValueError("started_at is required.")
        if unlock_id <= 0:
            raise ValueError("unlock_id must be positive.")
        if level <= 0:
            raise ValueError("level must be positive.")
        if not isinstance(safari_map, SafariMap):
            raise ValueError("safari_map must be a SafariMap.")
        if not isinstance(weather, SafariWeather):
            raise ValueError("weather must be a SafariWeather.")
        if not isinstance(time_of_day, SafariTimeOfDay):
            raise ValueError("time_of_day must be a SafariTimeOfDay.")
        configuration = SAFARI_LEVEL_CONFIGS.get(level)
        if configuration is None or configuration.encounter_count != total_encounters:
            raise ValueError("level does not match total_encounters.")
        if weather not in SAFARI_VALID_WEATHER_BY_MAP[safari_map]:
            raise ValueError("weather is not valid for safari_map.")
        if (
            SAFARI_ZONE_DEFINITION_BY_ZONE[initial_segment.zone].safari_map
            is not safari_map
        ):
            raise ValueError("initial segment zone must belong to safari_map.")

        copied_participants = tuple(participants)
        if not copied_participants:
            raise ValueError("Safari session requires participants.")
        participant_ids = [
            participant.trainer_id for participant in copied_participants
        ]
        if len(participant_ids) != len(set(participant_ids)):
            raise ValueError("Safari participant IDs must be unique.")

        schedule = SafariRouteSchedulePolicy().segment_lengths_for(total_encounters)
        if initial_segment.remaining_encounters != schedule[0]:
            raise ValueError("initial segment length does not match the schedule.")
        if initial_segment.source_option_id is not None:
            raise ValueError("initial segment cannot have a source option.")

        self._id = id
        self._guild_id = guild_id
        self._unlock_id = unlock_id
        self._level = level
        self._safari_map = safari_map
        self._weather = weather
        self._time_of_day = time_of_day
        self._participants_by_trainer = {
            participant.trainer_id: participant for participant in copied_participants
        }
        self._total_encounters = total_encounters
        self._route_segment_lengths = schedule
        self._route_segments = [initial_segment]
        self._current_segment_index = 0
        self._current_encounter: SafariEncounter | None = None
        self._current_route_vote: SafariRouteVote | None = None
        self._route_progress_history: list[SafariRouteProgressEntry] = []
        self._encounter_history: list[SafariEncounterHistoryEntry] = []
        self._completed_encounter_count = 0
        self._seen_species_ids: set[int] = set()
        self._extraordinary_flags = SafariExtraordinaryFlags()
        self._status = SafariSessionStatus.ENCOUNTER
        self._phase = SafariPhase.START
        self._finish_reason: SafariFinishReason | None = None
        self._started_at = started_at

        if not self._has_participant_with_balls():
            self._finish(SafariFinishReason.NO_BALLS_REMAINING)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def unlock_id(self) -> int:
        return self._unlock_id

    @property
    def level(self) -> int:
        return self._level

    @property
    def safari_map(self) -> SafariMap:
        return self._safari_map

    @property
    def weather(self) -> SafariWeather:
        return self._weather

    @property
    def time_of_day(self) -> SafariTimeOfDay:
        return self._time_of_day

    @property
    def participants_by_trainer(self) -> Mapping[int, SafariParticipant]:
        return MappingProxyType(dict(self._participants_by_trainer))

    @property
    def total_encounters(self) -> int:
        return self._total_encounters

    @property
    def route_segments(self) -> tuple[SafariRouteSegment, ...]:
        return tuple(self._route_segments)

    @property
    def current_segment(self) -> SafariRouteSegment:
        return self._route_segments[self._current_segment_index]

    @property
    def current_encounter(self) -> SafariEncounter | None:
        return self._current_encounter

    @property
    def current_route_vote(self) -> SafariRouteVote | None:
        return self._current_route_vote

    @property
    def route_progress_history(self) -> tuple[SafariRouteProgressEntry, ...]:
        return tuple(self._route_progress_history)

    @property
    def encounter_history(self) -> tuple[SafariEncounterHistoryEntry, ...]:
        return tuple(self._encounter_history)

    @property
    def completed_encounter_count(self) -> int:
        return self._completed_encounter_count

    @property
    def seen_species_ids(self) -> frozenset[int]:
        return frozenset(self._seen_species_ids)

    @property
    def extraordinary_flags(self) -> SafariExtraordinaryFlags:
        return self._extraordinary_flags

    @property
    def status(self) -> SafariSessionStatus:
        return self._status

    @property
    def phase(self) -> SafariPhase:
        return self._phase

    @property
    def finish_reason(self) -> SafariFinishReason | None:
        return self._finish_reason

    @property
    def started_at(self) -> datetime:
        return self._started_at

    def publish_encounter(self, encounter: SafariEncounter) -> None:
        self._require_status(SafariSessionStatus.ENCOUNTER)
        if self._current_encounter is not None:
            raise SafariInvalidSessionState("a Safari encounter is already active.")

        eligible_ids = frozenset(
            trainer_id
            for trainer_id, participant in self._participants_by_trainer.items()
            if participant.can_capture
        )
        if not eligible_ids:
            self._finish(SafariFinishReason.NO_BALLS_REMAINING)
            raise SafariSessionClosed("Safari session has no eligible participants.")

        encounter._set_eligible_participant_ids(eligible_ids)
        self._current_encounter = encounter
        self._seen_species_ids.update(slot.species_id for slot in encounter.slots)
        self._update_extraordinary_flags(encounter)

    def select_capture(
        self,
        trainer_id: int,
        slot_id: UUID,
        ball_count: int,
    ) -> None:
        self._require_status(SafariSessionStatus.ENCOUNTER)
        encounter = self._require_current_encounter()
        if trainer_id not in self._participants_by_trainer:
            raise ValueError("unknown Safari participant.")

        encounter._set_selection(
            SafariCaptureSelection(
                trainer_id=trainer_id,
                slot_id=slot_id,
                ball_count=ball_count,
            )
        )

    def confirm_selection(self, trainer_id: int) -> None:
        self._assert_not_closed()
        encounter = self._require_current_encounter()
        existing = encounter.selection_for(trainer_id)
        if existing is not None and existing.is_confirmed:
            raise SafariSelectionAlreadyConfirmed(
                "Safari capture selection is already confirmed."
            )
        self._require_status(SafariSessionStatus.ENCOUNTER)
        if existing is None:
            raise ValueError("participant has no Safari capture selection.")

        participant = self._participants_by_trainer.get(trainer_id)
        if participant is None:
            raise ValueError("unknown Safari participant.")

        participant.spend_balls(existing.ball_count)
        encounter._confirm_selection(trainer_id)
        self._begin_resolution_if_ready(encounter)

    def decline_capture(self, trainer_id: int) -> None:
        self._require_status(SafariSessionStatus.ENCOUNTER)
        encounter = self._require_current_encounter()
        if trainer_id not in self._participants_by_trainer:
            raise ValueError("unknown Safari participant.")

        encounter._decline(trainer_id)
        self._begin_resolution_if_ready(encounter)

    def apply_persisted_encounter_result(
        self,
        result: SafariPersistedEncounterResult,
        history_entry: SafariEncounterHistoryEntry | None = None,
    ) -> None:
        self._require_status(SafariSessionStatus.RESOLUTION)
        encounter = self._require_current_encounter()

        captures = self._validate_persisted_result(encounter, result)

        encounter._apply_persisted_result(result)
        if history_entry is not None:
            if history_entry.encounter.id != encounter.id:
                raise ValueError("history entry must match the current encounter.")
            if history_entry.resolution.encounter_id != encounter.id:
                raise ValueError("history entry must match the current encounter.")
        for trainer_id, creature_id in captures:
            self._participants_by_trainer[trainer_id].record_capture(creature_id)
        if history_entry is not None:
            self._encounter_history.append(history_entry)
        self.current_segment.complete_encounter()
        self._completed_encounter_count += 1
        self._current_encounter = None

        if self._completed_encounter_count == self._total_encounters:
            self._finish(SafariFinishReason.COMPLETED)
        elif not self._has_participant_with_balls():
            self._finish(SafariFinishReason.NO_BALLS_REMAINING)
        elif self.current_segment.is_complete:
            self._status = SafariSessionStatus.ROUTE_DECISION
        else:
            self._status = SafariSessionStatus.ENCOUNTER

    def start_route_vote(self, vote: SafariRouteVote) -> None:
        self._require_status(SafariSessionStatus.ROUTE_DECISION)
        if self._current_route_vote is not None:
            raise SafariInvalidSessionState("a Safari route vote is already active.")
        if any(
            option.source_zone != self.current_segment.zone for option in vote.options
        ):
            raise ValueError("route vote options must start in the current zone.")
        self._current_route_vote = vote

    def cast_route_vote(self, trainer_id: int, option_id: str) -> None:
        self._require_status(SafariSessionStatus.ROUTE_DECISION)
        vote = self._require_current_route_vote()
        vote.cast_vote(
            trainer_id=trainer_id,
            option_id=option_id,
            participant_ids=self._participants_by_trainer.keys(),
        )

    def resolve_route_vote(
        self,
        random_source: random.Random,
    ) -> SafariRouteVoteResult:
        self._require_status(SafariSessionStatus.ROUTE_DECISION)
        vote = self._require_current_route_vote()
        result = vote.resolve(random_source)

        next_index = self._current_segment_index + 1
        segment = SafariRouteSegment(
            zone=result.selected_option.destination_zone,
            remaining_encounters=self._route_segment_lengths[next_index],
            type_weight_modifiers=result.selected_option.type_weight_modifiers,
            allowed_events=result.selected_option.allowed_events,
            source_option_id=result.selected_option.id,
        )
        self._route_segments.append(segment)
        self._current_segment_index = next_index
        self._current_route_vote = None
        self._route_progress_history.append(
            SafariRouteProgressEntry(
                vote_result=result,
                destination_segment=segment,
                phase=self._phase_for_segment(next_index),
            )
        )
        self._phase = self._phase_for_segment(next_index)
        self._status = SafariSessionStatus.ENCOUNTER
        return result

    def cancel(self) -> None:
        if self._status == SafariSessionStatus.CANCELLED:
            return
        self._assert_not_closed()
        self._status = SafariSessionStatus.CANCELLED
        self._finish_reason = SafariFinishReason.ADMINISTRATIVE_ABORT

    def _validate_persisted_result(
        self,
        encounter: SafariEncounter,
        result: SafariPersistedEncounterResult,
    ) -> tuple[tuple[int, int], ...]:
        if encounter.status != SafariEncounterStatus.RESOLVING:
            raise SafariInvalidSessionState("Safari encounter is not resolving.")
        if result.encounter_id != encounter.id:
            raise ValueError("persisted result belongs to another encounter.")

        expected_slot_ids = {slot.id for slot in encounter.slots}
        result_slot_ids = {slot_result.slot_id for slot_result in result.slot_results}
        if result_slot_ids != expected_slot_ids:
            raise ValueError(
                "persisted result must cover every encounter slot exactly."
            )

        if not encounter.all_eligible_participants_decided:
            raise ValueError("not all eligible participants have decided.")
        if any(
            not selection.is_confirmed
            for selection in encounter.selections_by_trainer.values()
        ):
            raise ValueError("all Safari capture selections must be confirmed.")

        captures: list[tuple[int, int]] = []
        creature_ids: set[int] = set()
        for slot_result in result.slot_results:
            slot = next(
                slot for slot in encounter.slots if slot.id == slot_result.slot_id
            )
            if slot.status != SafariSlotStatus.AVAILABLE:
                raise ValueError("persisted result references a final slot.")
            if slot_result.capture is None:
                continue

            capture = slot_result.capture
            participant = self._participants_by_trainer.get(capture.trainer_id)
            if participant is None:
                raise ValueError("persisted capture references an unknown participant.")
            selection = encounter.selection_for(capture.trainer_id)
            if (
                selection is None
                or not selection.is_confirmed
                or selection.slot_id != capture.slot_id
            ):
                raise ValueError(
                    "persisted capture does not match a confirmed selection."
                )
            if capture.creature_id in creature_ids:
                raise ValueError("persisted creature IDs must be unique.")
            if capture.creature_id in participant.captured_creature_ids:
                raise ValueError("persisted creature is already recorded.")

            creature_ids.add(capture.creature_id)
            captures.append((capture.trainer_id, capture.creature_id))

        return tuple(captures)

    def _update_extraordinary_flags(self, encounter: SafariEncounter) -> None:
        opportunities = [slot.opportunity for slot in encounter.slots]
        current = self._extraordinary_flags
        self._extraordinary_flags = SafariExtraordinaryFlags(
            legendary_seen=(
                current.legendary_seen
                or any(item.species.metadata.is_legendary for item in opportunities)
            ),
            mythical_seen=(
                current.mythical_seen
                or any(item.species.metadata.is_mythical for item in opportunities)
            ),
            shiny_encounter_seen=(
                current.shiny_encounter_seen
                or any(item.is_shiny for item in opportunities)
            ),
            regional_herd_seen=(
                current.regional_herd_seen or encounter.is_regional_herd
            ),
        )

    def _begin_resolution_if_ready(self, encounter: SafariEncounter) -> None:
        if encounter.all_eligible_participants_decided:
            encounter._begin_resolution()
            self._status = SafariSessionStatus.RESOLUTION

    def _phase_for_segment(self, segment_index: int) -> SafariPhase:
        if segment_index == len(self._route_segment_lengths) - 1:
            return SafariPhase.FINAL
        if segment_index == 0:
            return SafariPhase.START
        return SafariPhase.DEVELOPMENT

    def _has_participant_with_balls(self) -> bool:
        return any(
            participant.can_capture
            for participant in self._participants_by_trainer.values()
        )

    def _require_current_encounter(self) -> SafariEncounter:
        if self._current_encounter is None:
            raise SafariInvalidSessionState("there is no active Safari encounter.")
        return self._current_encounter

    def _require_current_route_vote(self) -> SafariRouteVote:
        if self._current_route_vote is None:
            raise SafariInvalidSessionState("there is no active Safari route vote.")
        return self._current_route_vote

    def _require_status(self, expected: SafariSessionStatus) -> None:
        self._assert_not_closed()
        if self._status != expected:
            raise SafariInvalidSessionState(
                f"Safari session must be in {expected.value} status."
            )

    def _assert_not_closed(self) -> None:
        if self._status in (
            SafariSessionStatus.FINISHED,
            SafariSessionStatus.CANCELLED,
        ):
            raise SafariSessionClosed("Safari session is closed.")

    def _finish(self, reason: SafariFinishReason) -> None:
        self._status = SafariSessionStatus.FINISHED
        self._finish_reason = reason
