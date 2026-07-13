import random
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import UUID, uuid4

import pytest

from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    NotEnoughSafariBalls,
    SafariComposition,
    SafariEncounter,
    SafariEncounterSlot,
    SafariEncounterStatus,
    SafariFinishReason,
    SafariInvalidSessionState,
    SafariParticipant,
    SafariPersistedCapture,
    SafariPersistedEncounterResult,
    SafariPersistedSlotResult,
    SafariPhase,
    SafariRouteOption,
    SafariRouteSegment,
    SafariRouteVote,
    SafariSelectionAlreadyConfirmed,
    SafariSession,
    SafariSessionClosed,
    SafariSessionStatus,
    SafariSlotStatus,
    SafariZone,
)
from test.factories import create_species

NOW = datetime(2026, 7, 12, tzinfo=UTC)


def make_segment(
    zone: SafariZone = SafariZone.FOREST_ENTRANCE,
    remaining_encounters: int = 1,
) -> SafariRouteSegment:
    definition = SAFARI_ZONE_DEFINITION_BY_ZONE[zone]
    return SafariRouteSegment(
        zone=zone,
        remaining_encounters=remaining_encounters,
        type_weight_modifiers=definition.base_type_weights,
        allowed_events=definition.allowed_events,
    )


def make_session(
    participants: tuple[SafariParticipant, ...] | None = None,
) -> SafariSession:
    return SafariSession(
        id=uuid4(),
        guild_id=10,
        participants=participants or (SafariParticipant(1, 9, 9),),
        total_encounters=5,
        initial_segment=make_segment(),
        started_at=NOW,
    )


def make_encounter(
    species_ids: tuple[int, ...] = (25,),
    *,
    legendary: bool = False,
    mythical: bool = False,
    shiny: bool = False,
    composition: SafariComposition = SafariComposition.NORMAL,
    is_regional_herd: bool = False,
) -> SafariEncounter:
    slots = []
    for species_id in species_ids:
        opportunity = OpportunityFactory.create(
            create_species(
                id=species_id,
                is_legendary=legendary,
                is_mythical=mythical,
            )
        )
        opportunity.is_shiny = shiny
        slots.append(SafariEncounterSlot(uuid4(), opportunity))
    return SafariEncounter(
        uuid4(),
        composition,
        slots,
        is_regional_herd=is_regional_herd,
    )


def make_vote(source: SafariZone) -> SafariRouteVote:
    destinations = SAFARI_ZONE_DEFINITION_BY_ZONE[source].transitions[:2]
    options = []
    for destination in destinations:
        definition = SAFARI_ZONE_DEFINITION_BY_ZONE[destination]
        options.append(
            SafariRouteOption(
                id=f"{source.value}:{destination.value}",
                source_zone=source,
                destination_zone=destination,
                type_weight_modifiers=definition.base_type_weights,
                allowed_events=definition.allowed_events,
                narrative_key=(
                    f"{source.value.lower()}_to_{destination.value.lower()}"
                ),
            )
        )
    return SafariRouteVote(options, NOW)


def escaped_result(encounter: SafariEncounter) -> SafariPersistedEncounterResult:
    return SafariPersistedEncounterResult(
        encounter.id,
        tuple(
            SafariPersistedSlotResult(slot.id, SafariSlotStatus.ESCAPED)
            for slot in encounter.slots
        ),
    )


def resolve_declined_encounter(session: SafariSession) -> None:
    encounter = make_encounter()
    session.publish_encounter(encounter)
    for trainer_id in encounter.eligible_participant_ids:
        session.decline_capture(trainer_id)
    session.apply_persisted_encounter_result(escaped_result(encounter))


def resolve_route(session: SafariSession) -> None:
    vote = make_vote(session.current_segment.zone)
    session.start_route_vote(vote)
    session.resolve_route_vote(random.Random(1))


def test_session_validates_identity_participants_and_initial_segment():
    session = make_session()

    assert session.status == SafariSessionStatus.ENCOUNTER
    assert session.phase == SafariPhase.START
    assert session.completed_encounter_count == 0
    assert isinstance(session.participants_by_trainer, MappingProxyType)

    with pytest.raises(ValueError):
        SafariSession(
            UUID(int=0),
            10,
            (SafariParticipant(1, 9, 9),),
            5,
            make_segment(),
            NOW,
        )
    with pytest.raises(ValueError):
        SafariSession(uuid4(), 0, (), 5, make_segment(), NOW)
    with pytest.raises(ValueError):
        SafariSession(
            uuid4(),
            10,
            (SafariParticipant(1, 9, 9), SafariParticipant(1, 9, 9)),
            5,
            make_segment(),
            NOW,
        )
    with pytest.raises(ValueError):
        SafariSession(
            uuid4(),
            10,
            (SafariParticipant(1, 9, 9),),
            5,
            make_segment(remaining_encounters=2),
            NOW,
        )


def test_session_alone_calculates_and_freezes_eligible_participants():
    participant_with_balls = SafariParticipant(1, 3, 3)
    participant_without_balls = SafariParticipant(2, 3, 0)
    session = make_session((participant_with_balls, participant_without_balls))
    encounter = make_encounter()

    session.publish_encounter(encounter)
    participant_with_balls.spend_balls(3)

    assert encounter.eligible_participant_ids == frozenset({1})


def test_publish_tracks_species_and_flags_from_real_opportunities():
    session = make_session()
    encounter = make_encounter(
        (150, 151),
        legendary=True,
        mythical=True,
        shiny=True,
        is_regional_herd=True,
    )

    session.publish_encounter(encounter)

    assert session.seen_species_ids == frozenset({150, 151})
    assert session.extraordinary_flags.legendary_seen
    assert session.extraordinary_flags.mythical_seen
    assert session.extraordinary_flags.shiny_encounter_seen
    assert session.extraordinary_flags.regional_herd_seen


def test_composition_does_not_infer_legendary_or_regional_flags():
    session = make_session()
    encounter = make_encounter(composition=SafariComposition.LEGENDARY)

    session.publish_encounter(encounter)

    assert not session.extraordinary_flags.legendary_seen
    assert not session.extraordinary_flags.regional_herd_seen


def test_extraordinary_flags_remain_consumed_when_every_slot_escapes():
    session = make_session()
    encounter = make_encounter(
        legendary=True,
        shiny=True,
        composition=SafariComposition.LEGENDARY,
    )
    session.publish_encounter(encounter)
    session.decline_capture(1)

    session.apply_persisted_encounter_result(escaped_result(encounter))

    assert session.extraordinary_flags.legendary_seen
    assert session.extraordinary_flags.shiny_encounter_seen


@pytest.mark.parametrize(
    ("composition", "legendary", "mythical", "flag_name"),
    [
        (SafariComposition.LEGENDARY, True, False, "legendary_seen"),
        (SafariComposition.MYTHICAL, False, True, "mythical_seen"),
    ],
)
def test_publish_consumes_the_matching_extraordinary_species_flag(
    composition,
    legendary,
    mythical,
    flag_name,
):
    session = make_session()
    encounter = make_encounter(
        legendary=legendary,
        mythical=mythical,
        composition=composition,
    )

    session.publish_encounter(encounter)

    assert getattr(session.extraordinary_flags, flag_name)


def test_selection_replacement_does_not_spend_balls_until_confirmation():
    participant = SafariParticipant(1, 5, 5)
    session = make_session((participant,))
    encounter = make_encounter((1, 2))
    session.publish_encounter(encounter)

    session.select_capture(1, encounter.slots[0].id, 1)
    session.select_capture(1, encounter.slots[1].id, 2)

    assert participant.remaining_balls == 5
    assert encounter.selection_for(1).slot_id == encounter.slots[1].id
    session.confirm_selection(1)
    assert participant.remaining_balls == 3
    assert session.status == SafariSessionStatus.RESOLUTION


def test_second_confirmation_is_rejected_without_spending_again():
    participant = SafariParticipant(1, 3, 3)
    session = make_session((participant,))
    encounter = make_encounter()
    session.publish_encounter(encounter)
    session.select_capture(1, encounter.slots[0].id, 2)
    session.confirm_selection(1)

    with pytest.raises(SafariSelectionAlreadyConfirmed):
        session.confirm_selection(1)

    assert participant.remaining_balls == 1


def test_confirmation_rejects_more_balls_than_available_without_mutation():
    participant = SafariParticipant(1, 3, 1)
    session = make_session((participant,))
    encounter = make_encounter()
    session.publish_encounter(encounter)
    session.select_capture(1, encounter.slots[0].id, 2)

    with pytest.raises(NotEnoughSafariBalls):
        session.confirm_selection(1)

    assert participant.remaining_balls == 1
    assert not encounter.selection_for(1).is_confirmed
    assert session.status == SafariSessionStatus.ENCOUNTER


def test_all_eligible_decisions_move_session_to_resolution():
    session = make_session((SafariParticipant(1, 3, 3), SafariParticipant(2, 3, 3)))
    encounter = make_encounter()
    session.publish_encounter(encounter)
    session.select_capture(1, encounter.slots[0].id, 1)
    session.confirm_selection(1)

    assert session.status == SafariSessionStatus.ENCOUNTER
    session.decline_capture(2)

    assert session.status == SafariSessionStatus.RESOLUTION
    assert encounter.status == SafariEncounterStatus.RESOLVING


def test_persisted_result_records_capture_and_advances_segment():
    participant = SafariParticipant(1, 3, 3)
    session = make_session((participant,))
    encounter = make_encounter()
    slot = encounter.slots[0]
    session.publish_encounter(encounter)
    session.select_capture(1, slot.id, 1)
    session.confirm_selection(1)
    result = SafariPersistedEncounterResult(
        encounter.id,
        (
            SafariPersistedSlotResult(
                slot.id,
                SafariSlotStatus.CAPTURED,
                SafariPersistedCapture(1, slot.id, 501),
            ),
        ),
    )

    session.apply_persisted_encounter_result(result)

    assert participant.captured_creature_ids == (501,)
    assert slot.status == SafariSlotStatus.CAPTURED
    assert encounter.status == SafariEncounterStatus.RESOLVED
    assert session.completed_encounter_count == 1
    assert session.current_segment.is_complete
    assert session.status == SafariSessionStatus.ROUTE_DECISION


def test_partially_invalid_result_does_not_mutate_aggregate():
    first_participant = SafariParticipant(1, 3, 3)
    second_participant = SafariParticipant(2, 3, 3)
    session = make_session((first_participant, second_participant))
    encounter = make_encounter((1, 2))
    first_slot, second_slot = encounter.slots
    session.publish_encounter(encounter)
    session.select_capture(1, first_slot.id, 1)
    session.confirm_selection(1)
    session.select_capture(2, second_slot.id, 1)
    session.confirm_selection(2)
    invalid_result = SafariPersistedEncounterResult(
        encounter.id,
        (
            SafariPersistedSlotResult(
                first_slot.id,
                SafariSlotStatus.CAPTURED,
                SafariPersistedCapture(1, first_slot.id, 501),
            ),
            SafariPersistedSlotResult(
                second_slot.id,
                SafariSlotStatus.CAPTURED,
                SafariPersistedCapture(1, second_slot.id, 502),
            ),
        ),
    )

    with pytest.raises(ValueError, match="confirmed selection"):
        session.apply_persisted_encounter_result(invalid_result)

    assert first_participant.captured_creature_ids == ()
    assert second_participant.captured_creature_ids == ()
    assert first_slot.status == SafariSlotStatus.AVAILABLE
    assert second_slot.status == SafariSlotStatus.AVAILABLE
    assert encounter.status == SafariEncounterStatus.RESOLVING
    assert session.current_segment.remaining_encounters == 1
    assert session.completed_encounter_count == 0
    assert session.status == SafariSessionStatus.RESOLUTION


def test_persisted_result_requires_exact_slot_coverage_without_mutation():
    session = make_session()
    encounter = make_encounter((1, 2))
    session.publish_encounter(encounter)
    session.decline_capture(1)
    incomplete = SafariPersistedEncounterResult(
        encounter.id,
        (SafariPersistedSlotResult(encounter.slots[0].id, SafariSlotStatus.ESCAPED),),
    )

    with pytest.raises(ValueError, match="cover every"):
        session.apply_persisted_encounter_result(incomplete)

    assert all(slot.status == SafariSlotStatus.AVAILABLE for slot in encounter.slots)
    assert encounter.status == SafariEncounterStatus.RESOLVING
    assert session.completed_encounter_count == 0


def test_route_vote_builds_next_segment_from_selected_option_and_schedule():
    session = make_session()
    resolve_declined_encounter(session)
    vote = make_vote(session.current_segment.zone)
    session.start_route_vote(vote)

    result = session.resolve_route_vote(random.Random(1))

    assert session.current_segment.zone == result.selected_option.destination_zone
    assert session.current_segment.remaining_encounters == 2
    assert session.current_segment.source_option_id == result.selected_option.id
    assert session.phase == SafariPhase.DEVELOPMENT
    assert session.status == SafariSessionStatus.ENCOUNTER


def test_session_finishes_after_configured_encounter_total():
    session = make_session()

    for encounter_number in range(5):
        resolve_declined_encounter(session)
        if encounter_number in (0, 2):
            resolve_route(session)

    assert session.status == SafariSessionStatus.FINISHED
    assert session.finish_reason == SafariFinishReason.COMPLETED
    assert session.completed_encounter_count == 5
    assert session.phase == SafariPhase.FINAL


def test_session_finishes_when_no_participant_has_balls():
    participant = SafariParticipant(1, 1, 1)
    session = make_session((participant,))
    encounter = make_encounter()
    session.publish_encounter(encounter)
    session.select_capture(1, encounter.slots[0].id, 1)
    session.confirm_selection(1)
    session.apply_persisted_encounter_result(escaped_result(encounter))

    assert session.status == SafariSessionStatus.FINISHED
    assert session.finish_reason == SafariFinishReason.NO_BALLS_REMAINING


def test_cancelled_and_finished_sessions_reject_mutations():
    cancelled = make_session()
    cancelled.cancel()
    assert cancelled.status == SafariSessionStatus.CANCELLED
    assert cancelled.finish_reason == SafariFinishReason.ADMINISTRATIVE_ABORT
    cancelled.cancel()
    with pytest.raises(SafariSessionClosed):
        cancelled.publish_encounter(make_encounter())

    finished = make_session((SafariParticipant(1, 1, 0),))
    assert finished.status == SafariSessionStatus.FINISHED
    with pytest.raises(SafariSessionClosed):
        finished.cancel()


def test_route_vote_requires_current_zone_and_active_vote():
    session = make_session()
    resolve_declined_encounter(session)
    wrong_vote = make_vote(SafariZone.MOUNTAIN_FOOTHILL)

    with pytest.raises(ValueError, match="current zone"):
        session.start_route_vote(wrong_vote)
    with pytest.raises(SafariInvalidSessionState):
        session.resolve_route_vote(random.Random(1))
