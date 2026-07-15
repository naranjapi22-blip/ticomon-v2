from collections import Counter
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

import pytest

from core.capture import CaptureAttemptService
from core.capture.domain.capture_ball import CaptureBall
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SafariCapturePolicy,
    SafariCaptureResolver,
    SafariCaptureSelection,
    SafariComposition,
    SafariEncounter,
    SafariEncounterResolution,
    SafariEncounterSlot,
    SafariEncounterStatus,
    SafariParticipantOutcome,
    SafariSlotOutcome,
    SafariSlotStatus,
)
from core.safari.capture_resolution import (
    SafariCaptureResolutionError,
    _calculate_unique_attempt_chance,
    _unique_capture_target,
)
from test.factories import create_species


class RecordingChanceCalculator:
    def __init__(self, chance: float = 0.5) -> None:
        self.chance = chance
        self.calls = []

    def calculate(self, opportunity, capture_ball) -> float:
        self.calls.append((opportunity.failed_attempts, capture_ball))
        return self.chance


class ScriptedRandom:
    def __init__(self, *, rolls=(), shuffle_orders=()) -> None:
        self.rolls = list(rolls)
        self.shuffle_orders = [list(order) for order in shuffle_orders]
        self.shuffle_inputs = []

    def shuffle(self, queue) -> None:
        self.shuffle_inputs.append(tuple(queue))
        if not self.shuffle_orders:
            return
        ordered = self.shuffle_orders.pop(0)
        assert Counter(ordered) == Counter(queue)
        queue[:] = ordered

    def random(self) -> float:
        return self.rolls.pop(0)


def make_slot(
    species_id: int,
    *,
    failed_attempts: int = 0,
    capture_policy: SafariCapturePolicy = SafariCapturePolicy.UNIQUE,
) -> SafariEncounterSlot:
    opportunity = OpportunityFactory.create(create_species(id=species_id))
    opportunity.failed_attempts = failed_attempts
    return SafariEncounterSlot(uuid4(), opportunity, capture_policy)


def make_resolving_encounter(
    slots: tuple[SafariEncounterSlot, ...],
    selections: tuple[tuple[int, SafariEncounterSlot, int], ...] = (),
    *,
    composition: SafariComposition = SafariComposition.NORMAL,
    regional_herd: bool = False,
) -> SafariEncounter:
    encounter = SafariEncounter(
        uuid4(),
        composition,
        slots,
        is_regional_herd=regional_herd,
    )
    participant_ids = {trainer_id for trainer_id, _, _ in selections}
    if not participant_ids:
        participant_ids.add(999)
    encounter._set_eligible_participant_ids(frozenset(participant_ids))
    for trainer_id, slot, ball_count in selections:
        encounter._set_selection(
            SafariCaptureSelection(trainer_id, slot.id, ball_count)
        )
        encounter._confirm_selection(trainer_id)
    for trainer_id in participant_ids - {item[0] for item in selections}:
        encounter._decline(trainer_id)
    encounter._begin_resolution()
    return encounter


def make_resolver(chance: float, random_source: ScriptedRandom):
    calculator = RecordingChanceCalculator(chance)
    resolver = SafariCaptureResolver(
        CaptureAttemptService(calculator),  # type: ignore[arg-type]
        random_source,  # type: ignore[arg-type]
    )
    return resolver, calculator


def mark_unique_kind(slot: SafariEncounterSlot, kind: str) -> None:
    slot.opportunity.is_shiny = kind == "shiny"
    slot.opportunity.species = replace(
        slot.opportunity.species,
        metadata=replace(
            slot.opportunity.species.metadata,
            is_legendary=kind == "legendary",
            is_mythical=kind == "mythical",
        ),
    )


@pytest.mark.parametrize(
    ("kind", "target"),
    [("shiny", 0.35), ("legendary", 0.25), ("mythical", 0.15)],
)
def test_unique_capture_target_uses_conservative_objectives(kind, target):
    slot = make_slot(1)
    mark_unique_kind(slot, kind)

    assert _unique_capture_target(slot.opportunity) == target


@pytest.mark.parametrize("participant_count", (5, 20, 50, 100))
def test_unique_attempt_chance_is_stable_for_two_balls_per_participant(
    participant_count,
):
    slot = make_slot(1)
    mark_unique_kind(slot, "shiny")

    chance = _calculate_unique_attempt_chance(
        slot.opportunity,
        total_committed_balls=participant_count * 2,
        participant_count=participant_count,
    )

    assert chance == pytest.approx(1 - (1 - 0.35) ** (1 / (participant_count * 2)))


def test_unique_community_capture_increases_with_committed_balls():
    slot = make_slot(1)
    mark_unique_kind(slot, "legendary")
    chances = []

    for balls in (1, 2, 3):
        chance = _calculate_unique_attempt_chance(
            slot.opportunity,
            total_committed_balls=20 * balls,
            participant_count=20,
        )
        chances.append(1 - (1 - chance) ** (20 * balls))

    assert chances[0] < chances[1] < chances[2]


def test_unique_does_not_apply_personal_fatigue_to_attempt_chance():
    slot = make_slot(1)
    mark_unique_kind(slot, "shiny")
    encounter = make_resolving_encounter((slot,), ((1, slot, 3),))
    resolver, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.99, 0.99, 0.99)),
    )

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert len(outcome.attempts) == 3
    assert len({attempt.chance for attempt in outcome.attempts}) == 1
    assert [attempt.failed_attempts_before for attempt in outcome.attempts] == [
        0,
        1,
        2,
    ]


def test_unique_stops_at_first_success_and_unprocessed_participant_spends_nothing():
    slot = make_slot(1)
    mark_unique_kind(slot, "legendary")
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 3), (2, slot, 3)),
    )
    resolver, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.0,), shuffle_orders=((1, 2),)),
    )

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert len(outcome.attempts) == 1
    assert [item.attempts_executed for item in outcome.participant_outcomes] == [
        1,
        0,
    ]
    assert [item.balls_spent for item in outcome.participant_outcomes] == [1, 0]
    assert [item.captured for item in outcome.participant_outcomes] == [True, False]


def test_slot_without_selection_escapes_without_attempts():
    slot = make_slot(1)
    encounter = make_resolving_encounter((slot,))
    resolver, calculator = make_resolver(0.5, ScriptedRandom())

    resolution = resolver.resolve(encounter)
    outcome = resolution.slot_outcomes[0]

    assert outcome.status == SafariSlotStatus.ESCAPED
    assert outcome.winner_trainer_id is None
    assert outcome.attempts == ()
    assert outcome.attempts_executed == 0
    assert outcome.balls_committed == 0
    assert calculator.calls == []


def test_unique_participants_have_independent_fatigue():
    slot = make_slot(1)
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 1), (2, slot, 1)),
    )
    random_source = ScriptedRandom(
        rolls=(0.9, 0.8),
        shuffle_orders=((1, 2),),
    )
    resolver, calculator = make_resolver(0.5, random_source)

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert outcome.status == SafariSlotStatus.ESCAPED
    assert [attempt.trainer_id for attempt in outcome.attempts] == [1, 2]
    assert [attempt.failed_attempts_before for attempt in outcome.attempts] == [0, 0]
    assert [attempt.failed_attempts_after for attempt in outcome.attempts] == [1, 1]
    assert outcome.final_opportunity.failed_attempts == 0
    assert calculator.calls == [
        (0, CaptureBall.GREAT_BALL),
        (0, CaptureBall.GREAT_BALL),
    ]


def test_injected_shuffle_controls_winner_not_confirmation_order():
    slot = make_slot(1)
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 1), (2, slot, 1)),
    )
    random_source = ScriptedRandom(
        rolls=(0.1,),
        shuffle_orders=((2, 1),),
    )
    resolver, _ = make_resolver(0.5, random_source)

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert random_source.shuffle_inputs == [(1, 2)]
    assert outcome.winner_trainer_id == 2
    assert [attempt.trainer_id for attempt in outcome.attempts] == [2]


def test_first_success_stops_queue_but_all_balls_remain_committed():
    slot = make_slot(1)
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 3), (2, slot, 2)),
    )
    random_source = ScriptedRandom(
        rolls=(0.1,),
        shuffle_orders=((2, 1),),
    )
    resolver, calculator = make_resolver(0.5, random_source)

    resolution = resolver.resolve(encounter)
    outcome = resolution.slot_outcomes[0]

    assert outcome.status == SafariSlotStatus.CAPTURED
    assert outcome.winner_trainer_id == 2
    assert outcome.attempts_executed == 1
    assert outcome.balls_committed == 5
    assert outcome.balls_committed_by_trainer == {1: 3, 2: 2}
    assert resolution.balls_committed == 5
    assert resolution.attempts_executed == 1
    assert resolution.balls_committed_by_trainer == {1: 3, 2: 2}
    assert len(calculator.calls) == 1
    assert outcome.participant_outcomes == (
        SafariParticipantOutcome(
            trainer_id=2,
            balls_committed=2,
            attempts_executed=1,
            balls_spent=1,
            captured=True,
            final_opportunity=outcome.final_opportunity,
        ),
        SafariParticipantOutcome(
            trainer_id=1,
            balls_committed=3,
            attempts_executed=0,
            balls_spent=0,
            captured=False,
        ),
    )


def test_slot_outcome_accepts_multiple_participant_outcomes():
    slot = make_slot(1)
    participant_outcomes = (
        SafariParticipantOutcome(1, 2, 2, 2, False),
        SafariParticipantOutcome(2, 1, 0, 0, False),
    )
    outcome = SafariSlotOutcome(
        slot_id=slot.id,
        status=SafariSlotStatus.ESCAPED,
        winner_trainer_id=None,
        attempts=(),
        balls_committed_by_trainer={1: 2, 2: 1},
        final_opportunity=slot.opportunity,
        participant_outcomes=participant_outcomes,
    )

    assert outcome.participant_outcomes == participant_outcomes


def test_shared_slot_allows_multiple_independent_captures():
    slot = make_slot(1, capture_policy=SafariCapturePolicy.SHARED)
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 1), (2, slot, 1)),
    )
    resolver, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.1, 0.1)),
    )

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert outcome.status is SafariSlotStatus.CAPTURED
    assert outcome.winner_trainer_id is None
    assert [item.trainer_id for item in outcome.participant_outcomes] == [1, 2]
    assert all(item.captured for item in outcome.participant_outcomes)
    assert (
        len({id(item.final_opportunity) for item in outcome.participant_outcomes}) == 2
    )


def test_shared_slot_keeps_fatigue_and_attempts_independent():
    slot = make_slot(1, capture_policy=SafariCapturePolicy.SHARED)
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 2), (2, slot, 2)),
    )
    resolver, calculator = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.1, 0.9, 0.9)),
    )

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert [item.trainer_id for item in outcome.attempts] == [1, 1, 2, 2]
    assert [attempt.failed_attempts_before for attempt in outcome.attempts] == [
        0,
        1,
        0,
        1,
    ]
    assert calculator.calls == [
        (0, CaptureBall.GREAT_BALL),
        (1, CaptureBall.GREAT_BALL),
        (0, CaptureBall.GREAT_BALL),
        (1, CaptureBall.GREAT_BALL),
    ]
    assert [item.attempts_executed for item in outcome.participant_outcomes] == [
        2,
        2,
    ]
    assert [item.balls_spent for item in outcome.participant_outcomes] == [2, 2]
    assert [item.captured for item in outcome.participant_outcomes] == [True, False]


def test_shared_slot_stops_only_the_successful_participants_remaining_balls():
    slot = make_slot(1, capture_policy=SafariCapturePolicy.SHARED)
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 1), (2, slot, 3)),
    )
    resolver, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.1, 0.9, 0.9, 0.9)),
    )

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert [item.attempts_executed for item in outcome.participant_outcomes] == [
        1,
        3,
    ]
    assert [item.balls_spent for item in outcome.participant_outcomes] == [1, 3]
    assert outcome.attempts_executed == 4


def test_shared_slot_resolution_is_independent_of_selection_input_order():
    slot = make_slot(1, capture_policy=SafariCapturePolicy.SHARED)
    first_encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 2), (2, slot, 1)),
    )
    first_resolver, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.1, 0.9)),
    )
    first_outcome = first_resolver.resolve(first_encounter).slot_outcomes[0]

    slot = make_slot(1, capture_policy=SafariCapturePolicy.SHARED)
    second_encounter = make_resolving_encounter(
        (slot,),
        ((2, slot, 1), (1, slot, 2)),
    )
    second_resolver, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.1, 0.9)),
    )
    second_outcome = second_resolver.resolve(second_encounter).slot_outcomes[0]

    assert tuple(
        (item.trainer_id, item.attempts_executed, item.captured)
        for item in first_outcome.participant_outcomes
    ) == tuple(
        (item.trainer_id, item.attempts_executed, item.captured)
        for item in second_outcome.participant_outcomes
    )


def test_unique_participant_processes_all_balls_together():
    slot = make_slot(1)
    encounter = make_resolving_encounter((slot,), ((7, slot, 3),))
    random_source = ScriptedRandom(rolls=(0.9, 0.9, 0.9))
    resolver, _ = make_resolver(0.5, random_source)

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert random_source.shuffle_inputs == [(7,)]
    assert [attempt.trainer_id for attempt in outcome.attempts] == [7, 7, 7]
    assert [attempt.attempt_number for attempt in outcome.attempts] == [1, 2, 3]


def test_slots_have_independent_fatigue_and_stable_outcome_order():
    first = make_slot(1)
    second = make_slot(2)
    encounter = make_resolving_encounter(
        (first, second),
        ((1, first, 1), (2, second, 1)),
    )
    resolver, calculator = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.9)),
    )

    resolution = resolver.resolve(encounter)

    assert [outcome.slot_id for outcome in resolution.slot_outcomes] == [
        first.id,
        second.id,
    ]
    assert calculator.calls == [
        (0, CaptureBall.GREAT_BALL),
        (0, CaptureBall.GREAT_BALL),
    ]
    assert all(
        outcome.final_opportunity.failed_attempts == 0
        for outcome in resolution.slot_outcomes
    )
    assert all(
        outcome.participant_outcomes[0].final_opportunity.failed_attempts == 1
        for outcome in resolution.slot_outcomes
    )


def test_resolution_exposes_captured_escaped_and_winner_views():
    captured = make_slot(1)
    escaped = make_slot(2)
    encounter = make_resolving_encounter(
        (captured, escaped),
        ((1, captured, 1),),
    )
    resolver, _ = make_resolver(0.5, ScriptedRandom(rolls=(0.1,)))

    resolution = resolver.resolve(encounter)

    assert isinstance(resolution, SafariEncounterResolution)
    assert resolution.captured_slot_ids == (captured.id,)
    assert resolution.escaped_slot_ids == (escaped.id,)
    assert resolution.winners_by_slot == {captured.id: 1}


def test_resolver_does_not_modify_encounter_slots_selections_or_opportunities():
    slot = make_slot(1, failed_attempts=4)
    encounter = make_resolving_encounter((slot,), ((1, slot, 2),))
    selections_before = dict(encounter.selections_by_trainer)
    resolver, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.1)),
    )

    resolution = resolver.resolve(encounter)

    assert encounter.status == SafariEncounterStatus.RESOLVING
    assert slot.status == SafariSlotStatus.AVAILABLE
    assert slot.opportunity.failed_attempts == 4
    assert dict(encounter.selections_by_trainer) == selections_before
    assert resolution.slot_outcomes[0].final_opportunity is not slot.opportunity
    assert resolution.slot_outcomes[0].final_opportunity.failed_attempts == 1


def test_every_executed_attempt_uses_great_ball_and_no_creature_is_created():
    slot = make_slot(1)
    encounter = make_resolving_encounter((slot,), ((1, slot, 2),))
    resolver, calculator = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.1)),
    )

    with patch("core.creature.creature_factory.CreatureFactory.create") as create:
        outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert all(
        attempt.capture_ball == CaptureBall.GREAT_BALL for attempt in outcome.attempts
    )
    assert all(ball == CaptureBall.GREAT_BALL for _, ball in calculator.calls)
    create.assert_not_called()


def test_resolution_is_deterministic_with_equivalent_random_sources():
    slot = make_slot(1)
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 1), (2, slot, 1)),
    )
    first, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.1), shuffle_orders=((2, 1),)),
    )
    second, _ = make_resolver(
        0.5,
        ScriptedRandom(rolls=(0.9, 0.1), shuffle_orders=((2, 1),)),
    )

    assert first.resolve(encounter) == second.resolve(encounter)


@pytest.mark.parametrize(
    ("composition", "regional_herd"),
    [
        (SafariComposition.NORMAL, False),
        (SafariComposition.DUEL, False),
        (SafariComposition.HERD, False),
        (SafariComposition.BABY_NEST, False),
        (SafariComposition.REGIONAL, True),
        (SafariComposition.LEGENDARY, False),
        (SafariComposition.MYTHICAL, False),
    ],
)
def test_resolution_is_composition_agnostic(composition, regional_herd):
    slot = make_slot(1)
    slot.opportunity.is_shiny = True
    encounter = make_resolving_encounter(
        (slot,),
        ((1, slot, 1),),
        composition=composition,
        regional_herd=regional_herd,
    )
    resolver, _ = make_resolver(0.5, ScriptedRandom(rolls=(0.1,)))

    outcome = resolver.resolve(encounter).slot_outcomes[0]

    assert outcome.status == SafariSlotStatus.CAPTURED
    assert outcome.final_opportunity.is_shiny


@pytest.mark.parametrize(
    "status",
    [SafariEncounterStatus.OPEN, SafariEncounterStatus.RESOLVED],
)
def test_resolver_rejects_encounter_outside_resolution(status):
    encounter = SafariEncounter(
        uuid4(),
        SafariComposition.NORMAL,
        (make_slot(1),),
    )
    encounter._status = status
    resolver, _ = make_resolver(0.5, ScriptedRandom())

    with pytest.raises(SafariCaptureResolutionError, match="resolving"):
        resolver.resolve(encounter)


def test_resolver_rejects_unconfirmed_selection():
    slot = make_slot(1)
    encounter = SafariEncounter(
        uuid4(),
        SafariComposition.NORMAL,
        (slot,),
    )
    encounter._selections_by_trainer[1] = SafariCaptureSelection(1, slot.id, 1)
    encounter._status = SafariEncounterStatus.RESOLVING
    resolver, _ = make_resolver(0.5, ScriptedRandom())

    with pytest.raises(SafariCaptureResolutionError, match="confirmed"):
        resolver.resolve(encounter)
