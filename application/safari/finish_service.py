from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Callable

from application.safari.exceptions import (
    SafariSessionNotFinished,
    SafariSessionNotFound,
)
from application.safari.results import (
    FinishSafariResult,
    SafariCapturedCreatureSummary,
    SafariEncounterSlotSummary,
    SafariEncounterSummary,
    SafariExtraordinarySummary,
    SafariFinalSummary,
    SafariParticipantSummary,
    SafariRouteSegmentSummary,
    SafariRouteSummary,
    SafariTotalsSummary,
)
from core.safari.activity_repository import SafariActivityRepository
from core.safari.domain import (
    SafariFinishReason,
    SafariPhase,
    SafariSessionStatus,
    SafariSlotStatus,
)
from core.safari.history import (
    SafariCapturedCreatureSnapshot,
    SafariEncounterHistoryEntry,
)
from core.safari.session import SafariSession


class FinishSafariApplicationService:
    def __init__(
        self,
        activity_repository: SafariActivityRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._activity_repository = activity_repository
        self._clock = clock or (lambda: datetime.now(UTC))

    async def finish(self, guild_id: int) -> FinishSafariResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            self._require_finalized(session)
            finished_at = self._clock()
            summary = self._build_summary(session, finished_at)
            await self._activity_repository.clear_session(guild_id)
            return FinishSafariResult(session=session, summary=summary)

    async def _require_session(self, guild_id: int) -> SafariSession:
        session = await self._activity_repository.get_session(guild_id)
        if session is None:
            raise SafariSessionNotFound("Safari session was not found.")
        return session

    @staticmethod
    def _require_finalized(session: SafariSession) -> None:
        if session.status is not SafariSessionStatus.FINISHED:
            raise SafariSessionNotFinished("Safari session cannot be finished yet.")
        if session.current_encounter is not None:
            raise SafariSessionNotFinished(
                "Safari session still has an active encounter."
            )
        if session.current_route_vote is not None:
            raise SafariSessionNotFinished(
                "Safari session still has an active route vote."
            )
        if session.finish_reason is None:
            raise SafariSessionNotFinished(
                "Safari session does not have a finish reason."
            )

    def _build_summary(
        self,
        session: SafariSession,
        finished_at: datetime,
    ) -> SafariFinalSummary:
        route = self._build_route_summary(session)
        encounters = tuple(
            self._build_encounter_summary(entry) for entry in session.encounter_history
        )
        ranking = self._build_ranking(session, encounters)
        totals = self._build_totals(session, encounters)

        return SafariFinalSummary(
            guild_id=session.guild_id,
            session_id=session.id,
            level=session.level,
            safari_map=session.safari_map,
            weather=session.weather,
            time_of_day=session.time_of_day,
            started_at=session.started_at,
            finished_at=finished_at,
            finish_reason=self._finish_reason(session),
            ranking=ranking,
            route=route,
            encounters=encounters,
            totals=totals,
            extraordinary=SafariExtraordinarySummary(
                legendary_seen=session.extraordinary_flags.legendary_seen,
                mythical_seen=session.extraordinary_flags.mythical_seen,
                shiny_encounter_seen=session.extraordinary_flags.shiny_encounter_seen,
                regional_herd_seen=session.extraordinary_flags.regional_herd_seen,
            ),
        )

    def _build_route_summary(self, session: SafariSession) -> SafariRouteSummary:
        segments = [
            SafariRouteSegmentSummary(
                zone=session.route_segments[0].zone,
                phase=SafariPhase.START,
                remaining_encounters=session.route_segments[0].remaining_encounters,
                source_option_id=None,
            )
        ]
        for entry in session.route_progress_history:
            segments.append(
                SafariRouteSegmentSummary(
                    zone=entry.destination_segment.zone,
                    phase=entry.phase,
                    remaining_encounters=entry.destination_segment.remaining_encounters,
                    source_option_id=entry.destination_segment.source_option_id,
                    vote_result=entry.vote_result,
                )
            )
        return SafariRouteSummary(
            safari_map=session.safari_map,
            weather=session.weather,
            time_of_day=session.time_of_day,
            segments=tuple(segments),
        )

    def _build_encounter_summary(
        self,
        entry: SafariEncounterHistoryEntry,
    ) -> SafariEncounterSummary:
        captured_by_slot = {
            snapshot.slot_id: snapshot for snapshot in entry.captured_creatures
        }
        slot_summaries = []
        for outcome in entry.resolution.slot_outcomes:
            slot = next(
                slot for slot in entry.encounter.slots if slot.id == outcome.slot_id
            )
            captured_snapshot = captured_by_slot.get(outcome.slot_id)
            slot_summaries.append(
                SafariEncounterSlotSummary(
                    slot_id=outcome.slot_id,
                    species=slot.opportunity.species,
                    status=outcome.status,
                    winner_trainer_id=outcome.winner_trainer_id,
                    attempts_executed=outcome.attempts_executed,
                    balls_committed=outcome.balls_committed,
                    captured_creature=(
                        self._captured_creature_summary(captured_snapshot)
                        if captured_snapshot is not None
                        else None
                    ),
                )
            )

        return SafariEncounterSummary(
            encounter_id=entry.encounter.id,
            composition=entry.encounter.composition,
            is_regional_herd=entry.encounter.is_regional_herd,
            slot_summaries=tuple(slot_summaries),
            captured_slot_count=sum(
                1
                for outcome in entry.resolution.slot_outcomes
                if outcome.status is SafariSlotStatus.CAPTURED
            ),
            escaped_slot_count=sum(
                1
                for outcome in entry.resolution.slot_outcomes
                if outcome.status is SafariSlotStatus.ESCAPED
            ),
            attempts_executed=entry.resolution.attempts_executed,
            balls_committed=entry.resolution.balls_committed,
        )

    def _build_ranking(
        self,
        session: SafariSession,
        encounters: tuple[SafariEncounterSummary, ...],
    ) -> tuple[SafariParticipantSummary, ...]:
        captures_by_trainer: dict[int, list[SafariCapturedCreatureSummary]] = (
            defaultdict(list)
        )
        attempts_by_trainer: dict[int, int] = defaultdict(int)
        slots_won_by_trainer: dict[int, int] = defaultdict(int)
        encounters_participated_by_trainer: dict[int, int] = defaultdict(int)

        for encounter_entry, _encounter_summary in zip(
            session.encounter_history,
            encounters,
            strict=True,
        ):
            for trainer_id in encounter_entry.eligible_participant_ids:
                encounters_participated_by_trainer[trainer_id] += 1

            for snapshot in encounter_entry.captured_creatures:
                captures_by_trainer[snapshot.trainer_id].append(
                    self._captured_creature_summary(snapshot)
                )

            for outcome in encounter_entry.resolution.slot_outcomes:
                if outcome.winner_trainer_id is not None:
                    slots_won_by_trainer[outcome.winner_trainer_id] += 1
                for attempt in outcome.attempts:
                    attempts_by_trainer[attempt.trainer_id] += 1

        participant_data = []
        for trainer_id, participant in session.participants_by_trainer.items():
            captured_creatures = tuple(captures_by_trainer.get(trainer_id, ()))
            capture_count = len(captured_creatures)
            shiny_capture_count = sum(
                1 for creature in captured_creatures if creature.is_shiny
            )
            participant_data.append(
                (
                    trainer_id,
                    captured_creatures,
                    capture_count,
                    shiny_capture_count,
                    participant.initial_balls,
                    participant.balls_spent,
                    participant.remaining_balls,
                    attempts_by_trainer.get(trainer_id, 0),
                    slots_won_by_trainer.get(trainer_id, 0),
                    encounters_participated_by_trainer.get(trainer_id, 0),
                )
            )

        participant_data.sort(
            key=lambda item: (
                -item[2],
                -item[3],
                -item[6],
                item[5],
                item[0],
            )
        )

        return tuple(
            SafariParticipantSummary(
                rank=index,
                trainer_id=trainer_id,
                capture_count=capture_count,
                shiny_capture_count=shiny_capture_count,
                captured_creatures=captured_creatures,
                initial_balls=initial_balls,
                balls_used=balls_used,
                balls_remaining=balls_remaining,
                attempts_executed=attempts_executed,
                slots_won=slots_won,
                encounters_participated=encounters_participated,
            )
            for index, (
                trainer_id,
                captured_creatures,
                capture_count,
                shiny_capture_count,
                initial_balls,
                balls_used,
                balls_remaining,
                attempts_executed,
                slots_won,
                encounters_participated,
            ) in enumerate(participant_data, start=1)
        )

    @staticmethod
    def _build_totals(
        session: SafariSession,
        encounters: tuple[SafariEncounterSummary, ...],
    ) -> SafariTotalsSummary:
        return SafariTotalsSummary(
            encounters_completed=session.completed_encounter_count,
            pokemon_seen=len(session.seen_species_ids),
            slots_captured=sum(
                encounter.captured_slot_count for encounter in encounters
            ),
            slots_escaped=sum(encounter.escaped_slot_count for encounter in encounters),
            attempts_executed=sum(
                encounter.attempts_executed for encounter in encounters
            ),
            balls_committed=sum(encounter.balls_committed for encounter in encounters),
        )

    @staticmethod
    def _captured_creature_summary(
        snapshot: SafariCapturedCreatureSnapshot,
    ) -> SafariCapturedCreatureSummary:
        assert snapshot.creature.collection_number is not None
        return SafariCapturedCreatureSummary(
            slot_id=snapshot.slot_id,
            trainer_id=snapshot.trainer_id,
            creature_id=snapshot.creature_id,
            species=snapshot.creature.species,
            collection_number=snapshot.creature.collection_number,
            is_shiny=snapshot.creature.is_shiny,
            current_form=snapshot.creature.current_form,
        )

    @staticmethod
    def _finish_reason(session: SafariSession) -> SafariFinishReason:
        assert session.finish_reason is not None
        return session.finish_reason
