from __future__ import annotations

import random
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from application.safari import (
    FinishSafariApplicationService,
    SafariExtraordinarySummary,
    SafariFinalSummary,
    SafariSessionNotFinished,
    SafariSessionNotFound,
)
from application.safari.activity_state import SafariActivityTracker
from core.capture.domain.capture_ball import CaptureBall
from core.safari import (
    SafariCaptureAttempt,
    SafariCapturedCreatureSnapshot,
    SafariEncounterHistoryEntry,
    SafariEncounterResolution,
    SafariExtraordinaryFlags,
    SafariFinishReason,
    SafariParticipant,
    SafariPhase,
    SafariRouteProgressEntry,
    SafariRouteSegment,
    SafariSession,
    SafariSessionStatus,
    SafariSlotOutcome,
    SafariSlotStatus,
)
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from test.builders.creature_builder import CreatureBuilder
from test.unit.safari.test_session import make_encounter, make_session, make_vote

NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)


def _service(
    activity: InMemorySafariActivityRepository,
    tracker: SafariActivityTracker,
) -> FinishSafariApplicationService:
    return FinishSafariApplicationService(
        activity_repository=activity,
        activity_tracker=tracker,
        clock=lambda: NOW,
    )


def _capture_attempt(
    trainer_id: int,
    slot_id,
    attempt_number: int,
    success: bool,
    failed_attempts_before: int,
    failed_attempts_after: int,
) -> SafariCaptureAttempt:
    return SafariCaptureAttempt(
        trainer_id=trainer_id,
        slot_id=slot_id,
        attempt_number=attempt_number,
        success=success,
        chance=1.0 if success else 0.0,
        roll=0.0 if success else 1.0,
        failed_attempts_before=failed_attempts_before,
        failed_attempts_after=failed_attempts_after,
        capture_ball=CaptureBall.GREAT_BALL,
    )


def _captured_creature(
    *,
    slot_id,
    trainer_id: int,
    creature_id: int,
    collection_number: int,
    species_id: int,
    shiny: bool = False,
    variant_id: int | None = None,
    variant_name: str | None = None,
) -> SafariCapturedCreatureSnapshot:
    creature = (
        CreatureBuilder()
        .with_species(make_encounter((species_id,)).slots[0].opportunity.species)
        .with_trainer_id(trainer_id)
        .with_id(creature_id)
        .with_collection_number(collection_number)
        .build()
    )
    if shiny:
        creature.is_shiny = True
    if variant_id is not None and variant_name is not None:
        from core.species.variant import Variant

        creature.current_form = Variant(id=variant_id, name=variant_name)
    return SafariCapturedCreatureSnapshot(
        slot_id=slot_id,
        trainer_id=trainer_id,
        creature_id=creature_id,
        creature=creature,
    )


def _finalized_session() -> SafariSession:
    session = make_session(
        (SafariParticipant(1, 9, 7), SafariParticipant(2, 9, 8)),
    )
    encounter = make_encounter((25, 26, 27))
    first_slot, second_slot, third_slot = encounter.slots

    first_outcome = SafariSlotOutcome(
        slot_id=first_slot.id,
        status=SafariSlotStatus.CAPTURED,
        winner_trainer_id=1,
        attempts=(_capture_attempt(1, first_slot.id, 1, True, 0, 0),),
        balls_committed_by_trainer={1: 1},
        final_opportunity=first_slot.opportunity,
    )
    second_outcome = SafariSlotOutcome(
        slot_id=second_slot.id,
        status=SafariSlotStatus.CAPTURED,
        winner_trainer_id=1,
        attempts=(_capture_attempt(1, second_slot.id, 1, True, 0, 0),),
        balls_committed_by_trainer={1: 1},
        final_opportunity=second_slot.opportunity,
    )
    third_outcome = SafariSlotOutcome(
        slot_id=third_slot.id,
        status=SafariSlotStatus.ESCAPED,
        winner_trainer_id=None,
        attempts=(_capture_attempt(2, third_slot.id, 1, False, 0, 1),),
        balls_committed_by_trainer={2: 1},
        final_opportunity=replace(third_slot.opportunity, failed_attempts=1),
    )
    resolution = SafariEncounterResolution(
        encounter.id,
        (first_outcome, second_outcome, third_outcome),
    )
    capture_one = _captured_creature(
        slot_id=first_slot.id,
        trainer_id=1,
        creature_id=101,
        collection_number=7,
        species_id=first_slot.opportunity.species.id,
    )
    capture_two = _captured_creature(
        slot_id=second_slot.id,
        trainer_id=1,
        creature_id=102,
        collection_number=8,
        species_id=second_slot.opportunity.species.id,
        shiny=True,
        variant_id=44,
        variant_name="Forest Form",
    )
    session._encounter_history.append(
        SafariEncounterHistoryEntry(
            encounter=encounter,
            resolution=resolution,
            captured_creatures=(capture_one, capture_two),
            eligible_participant_ids=frozenset({1, 2}),
        )
    )
    session._seen_species_ids.update(
        {
            first_slot.opportunity.species.id,
            second_slot.opportunity.species.id,
            third_slot.opportunity.species.id,
        }
    )
    session._extraordinary_flags = SafariExtraordinaryFlags(
        legendary_seen=True,
        mythical_seen=True,
        shiny_encounter_seen=True,
        regional_herd_seen=True,
    )

    vote = make_vote(session.current_segment.zone)
    vote_result = vote.resolve(random.Random(1))
    destination_segment = SafariRouteSegment(
        zone=vote_result.selected_option.destination_zone,
        remaining_encounters=1,
        type_weight_modifiers=vote_result.selected_option.type_weight_modifiers,
        allowed_events=vote_result.selected_option.allowed_events,
        source_option_id=vote_result.selected_option.id,
    )
    session._route_segments.append(destination_segment)
    session._route_progress_history.append(
        SafariRouteProgressEntry(
            vote_result=vote_result,
            destination_segment=destination_segment,
            phase=SafariPhase.DEVELOPMENT,
        )
    )
    session._completed_encounter_count = 1
    session._status = SafariSessionStatus.FINISHED
    session._finish_reason = SafariFinishReason.COMPLETED
    return session


@pytest.mark.asyncio
async def test_finish_rejects_missing_session():
    service = _service(InMemorySafariActivityRepository(), SafariActivityTracker())

    with pytest.raises(SafariSessionNotFound):
        await service.finish(100)


@pytest.mark.asyncio
async def test_finish_builds_summary_and_clears_activity():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    session = _finalized_session()
    await activity.save_session(session)
    service = _service(activity, tracker)

    result = await service.finish(session.guild_id)

    assert result.session is session
    assert isinstance(result.summary, SafariFinalSummary)
    assert result.summary.guild_id == session.guild_id
    assert result.summary.finished_at == NOW
    assert result.summary.finish_reason is SafariFinishReason.COMPLETED
    assert result.summary.extraordinary == SafariExtraordinarySummary(
        legendary_seen=True,
        mythical_seen=True,
        shiny_encounter_seen=True,
        regional_herd_seen=True,
    )
    assert result.summary.ranking[0].trainer_id == 1
    assert result.summary.ranking[0].rank == 1
    assert result.summary.ranking[0].capture_count == 2
    assert result.summary.ranking[0].shiny_capture_count == 1
    assert result.summary.ranking[0].balls_used == 2
    assert result.summary.ranking[0].balls_remaining == 7
    assert result.summary.ranking[0].attempts_executed == 2
    assert result.summary.ranking[0].slots_won == 2
    assert result.summary.ranking[0].encounters_participated == 1
    assert result.summary.ranking[0].captured_creatures[1].current_form is not None
    assert result.summary.ranking[1].trainer_id == 2
    assert result.summary.ranking[1].rank == 2
    assert result.summary.ranking[1].capture_count == 0
    assert result.summary.ranking[1].balls_used == 1
    assert result.summary.ranking[1].balls_remaining == 8
    assert result.summary.ranking[1].attempts_executed == 1
    assert result.summary.ranking[1].slots_won == 0
    assert result.summary.route.segments[0].phase is SafariPhase.START
    assert result.summary.route.segments[1].phase is SafariPhase.DEVELOPMENT
    assert result.summary.route.segments[1].vote_result is not None
    assert result.summary.route.segments[1].vote_result.was_tiebreak is False
    assert result.summary.route.segments[1].vote_result.selected_option.id
    assert result.summary.totals.encounters_completed == 1
    assert result.summary.totals.pokemon_seen == 3
    assert result.summary.totals.slots_captured == 2
    assert result.summary.totals.slots_escaped == 1
    assert result.summary.totals.attempts_executed == 3
    assert result.summary.totals.balls_committed == 3
    assert await activity.get_session(session.guild_id) is None
    assert tracker.get(session.guild_id).selection_deadline is None
    assert tracker.get(session.guild_id).route_vote_deadline is None

    with pytest.raises(SafariSessionNotFound):
        await service.finish(session.guild_id)


@pytest.mark.asyncio
async def test_finish_rejects_session_with_pending_encounter():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    session = _finalized_session()
    session._current_encounter = make_encounter((25,))
    await activity.save_session(session)
    service = _service(activity, tracker)

    with pytest.raises(SafariSessionNotFinished):
        await service.finish(session.guild_id)


@pytest.mark.asyncio
async def test_finish_rejects_session_with_pending_route_vote():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    session = _finalized_session()
    session._current_route_vote = make_vote(session.current_segment.zone)
    await activity.save_session(session)
    service = _service(activity, tracker)

    with pytest.raises(SafariSessionNotFinished):
        await service.finish(session.guild_id)


@pytest.mark.asyncio
async def test_finish_ranking_uses_deterministic_tiebreakers():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    session = make_session(
        (
            SafariParticipant(1, 9, 4),
            SafariParticipant(2, 9, 6),
            SafariParticipant(3, 8, 6),
        ),
    )
    encounter = make_encounter((25, 26, 27))
    slot_1, slot_2, slot_3 = encounter.slots
    resolution = SafariEncounterResolution(
        encounter.id,
        (
            SafariSlotOutcome(
                slot_id=slot_1.id,
                status=SafariSlotStatus.CAPTURED,
                winner_trainer_id=1,
                attempts=(_capture_attempt(1, slot_1.id, 1, True, 0, 0),),
                balls_committed_by_trainer={1: 1},
                final_opportunity=slot_1.opportunity,
            ),
            SafariSlotOutcome(
                slot_id=slot_2.id,
                status=SafariSlotStatus.CAPTURED,
                winner_trainer_id=2,
                attempts=(_capture_attempt(2, slot_2.id, 1, True, 0, 0),),
                balls_committed_by_trainer={2: 1},
                final_opportunity=slot_2.opportunity,
            ),
            SafariSlotOutcome(
                slot_id=slot_3.id,
                status=SafariSlotStatus.CAPTURED,
                winner_trainer_id=3,
                attempts=(_capture_attempt(3, slot_3.id, 1, True, 0, 0),),
                balls_committed_by_trainer={3: 1},
                final_opportunity=slot_3.opportunity,
            ),
        ),
    )
    session._encounter_history.append(
        SafariEncounterHistoryEntry(
            encounter=encounter,
            resolution=resolution,
            captured_creatures=(
                _captured_creature(
                    slot_id=slot_1.id,
                    trainer_id=1,
                    creature_id=201,
                    collection_number=1,
                    species_id=slot_1.opportunity.species.id,
                ),
                _captured_creature(
                    slot_id=slot_2.id,
                    trainer_id=2,
                    creature_id=202,
                    collection_number=2,
                    species_id=slot_2.opportunity.species.id,
                ),
                _captured_creature(
                    slot_id=slot_3.id,
                    trainer_id=3,
                    creature_id=203,
                    collection_number=3,
                    species_id=slot_3.opportunity.species.id,
                ),
            ),
            eligible_participant_ids=frozenset({1, 2, 3}),
        )
    )
    session._completed_encounter_count = 1
    session._status = SafariSessionStatus.FINISHED
    session._finish_reason = SafariFinishReason.COMPLETED
    await activity.save_session(session)
    service = _service(activity, tracker)

    result = await service.finish(session.guild_id)

    assert [participant.trainer_id for participant in result.summary.ranking] == [
        3,
        2,
        1,
    ]
    assert [participant.rank for participant in result.summary.ranking] == [1, 2, 3]


@pytest.mark.asyncio
async def test_finish_rejects_active_session_and_keeps_activity():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    session = make_session()
    await activity.save_session(session)
    service = _service(activity, tracker)

    with pytest.raises(SafariSessionNotFinished):
        await service.finish(session.guild_id)

    assert await activity.get_session(session.guild_id) is session


@pytest.mark.asyncio
async def test_finish_clears_activity_when_summary_build_fails():
    class _FailingFinishService(FinishSafariApplicationService):
        def _build_summary(self, session, finished_at):
            raise RuntimeError("summary")

    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    session = _finalized_session()
    await activity.save_session(session)
    service = _FailingFinishService(
        activity_repository=activity,
        activity_tracker=tracker,
        clock=lambda: NOW,
    )

    with pytest.raises(RuntimeError, match="summary"):
        await service.finish(session.guild_id)

    assert await activity.get_session(session.guild_id) is None
    assert tracker.get(session.guild_id).selection_deadline is None
    assert tracker.get(session.guild_id).route_vote_deadline is None
