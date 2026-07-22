import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

import pytest

from application.safari import (
    SafariCaptureApplicationService,
    SafariCaptureSelectionNotFound,
    SafariCaptureSelectionState,
    SafariCaptureSelectionUnavailable,
    SelectSafariCaptureResult,
)
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_unit_of_work import (
    CaptureTransaction,
    CaptureUnitOfWork,
    SaveUnlockResult,
)
from core.capture.attempt_service import CaptureAttemptService
from core.capture.domain.capture_ball import CaptureBall
from core.creature.ivs import IVs
from core.creature.size import Size
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SafariCaptureResolver,
    SafariComposition,
    SafariEncounter,
    SafariEncounterSlot,
    SafariEncounterStatus,
    SafariGeneratedEncounter,
    SafariParticipant,
    SafariSelectionAlreadyConfirmed,
    SafariSession,
    SafariSessionStatus,
    SafariThematicEvent,
)
from core.safari.participant import NotEnoughSafariBalls
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from test.factories import create_species
from test.unit.safari.test_session import make_encounter, make_session


class _AlwaysSuccessChanceCalculator:
    def calculate(self, opportunity, capture_ball) -> float:
        assert capture_ball is CaptureBall.GREAT_BALL
        return 1.0


class _DeterministicRandom:
    def shuffle(self, queue) -> None:
        queue.sort()

    def random(self) -> float:
        return 0.0


class _EncounterGenerator:
    def __init__(self, species=None) -> None:
        self.context = None
        self.compositions = None
        self.species = species or create_species(id=999)

    async def generate_with_events(self, context, compositions):
        self.context = context
        self.compositions = compositions
        opportunity = OpportunityFactory.create(self.species)
        encounter = SafariEncounter(
            uuid4(),
            SafariComposition.NORMAL,
            (SafariEncounterSlot(uuid4(), opportunity),),
        )
        return SafariGeneratedEncounter(encounter, SafariThematicEvent.NONE)


class _Transaction(CaptureTransaction):
    def __init__(self, *, fail_at: str | None = None, events: list[str] | None = None):
        self.fail_at = fail_at
        self.events = events if events is not None else []
        self._creature_counts: dict[int, int] = {}
        self._inventories: dict[int, CandyInventory] = {}
        self.saved_creatures = []
        self.saved_inventories = []
        self.activities = []

    async def save_creature(self, creature):
        self._record("creature")
        number = self._creature_counts.get(creature.trainer_id, 0) + 1
        self._creature_counts[creature.trainer_id] = number
        saved = replace(
            creature,
            id=100 + len(self.saved_creatures) + 1,
            collection_number=number,
        )
        self.saved_creatures.append(saved)
        return saved

    async def get_candy_inventory(self, trainer_id):
        self._record("candies_get")
        return self._inventories.get(trainer_id, CandyInventory())

    async def save_candy_inventory(self, trainer_id, inventory):
        self._record("candies_save")
        self.saved_inventories.append((trainer_id, inventory))
        self._inventories[trainer_id] = inventory

    async def record_achievement_activity(self, activity):
        self._record("achievement_activity")
        self.activities.append(activity)
        return True

    async def save_unlock(self, unlock):
        return SaveUnlockResult(unlock, created=True)

    def _record(self, operation: str) -> None:
        self.events.append(operation)
        if self.fail_at == operation:
            raise RuntimeError(operation)


class _UnitOfWork(CaptureUnitOfWork):
    def __init__(self, transaction: _Transaction):
        self.transaction_data = transaction
        self.events = transaction.events

    @asynccontextmanager
    async def transaction(self):
        self.events.append("begin")
        try:
            yield self.transaction_data
        except Exception:
            self.events.append("rollback")
            raise
        else:
            self.events.append("commit")


class _TrackingActivityRepository(InMemorySafariActivityRepository):
    def __init__(self) -> None:
        super().__init__()
        self.saved_sessions: list[int] = []

    async def save_session(self, session):
        self.saved_sessions.append(session.guild_id)
        await super().save_session(session)


def _capture_service(
    *,
    activity: InMemorySafariActivityRepository | None = None,
    unit_of_work: CaptureUnitOfWork | None = None,
    species=None,
) -> SafariCaptureApplicationService:
    if activity is None:
        activity = _TrackingActivityRepository()
    if unit_of_work is None:
        unit_of_work = _UnitOfWork(_Transaction())
    resolver = SafariCaptureResolver(
        CaptureAttemptService(_AlwaysSuccessChanceCalculator()),
        _DeterministicRandom(),
    )
    generator = _EncounterGenerator(species=species)
    return SafariCaptureApplicationService(
        activity_repository=activity,
        capture_resolver=resolver,
        unit_of_work=unit_of_work,
        reward_policy=RewardPolicy(),
        encounter_generator=generator,
        random_source=_DeterministicRandom(),
    )


def _published_session(participants: tuple[SafariParticipant, ...]) -> SafariSession:
    session = make_session(participants)
    encounter = make_encounter((25, 26))
    session.publish_encounter(encounter)
    return session


@pytest.mark.asyncio
async def test_select_capture_replaces_pending_selection_without_spending_balls():
    activity = _TrackingActivityRepository()
    session = _published_session(
        (SafariParticipant(1, 3, 3), SafariParticipant(2, 3, 3))
    )
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    first = await service.select_capture(
        session.guild_id,
        1,
        session.current_encounter.slots[0].id,
        1,
    )
    second = await service.select_capture(
        session.guild_id,
        1,
        session.current_encounter.slots[1].id,
        2,
    )

    assert isinstance(first, SelectSafariCaptureResult)
    assert first.state is SafariCaptureSelectionState.PENDING
    assert second.selection.slot_id == session.current_encounter.slots[1].id
    assert second.balls_available == 3
    assert session.participants_by_trainer[1].remaining_balls == 3
    assert activity.saved_sessions == [
        session.guild_id,
        session.guild_id,
        session.guild_id,
    ]


@pytest.mark.asyncio
async def test_select_capture_rejects_invalid_participant_slot_or_ball_count():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 2),))
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    with pytest.raises(SafariCaptureSelectionUnavailable):
        await service.select_capture(
            session.guild_id, 99, session.current_encounter.slots[0].id, 1
        )

    with pytest.raises(SafariCaptureSelectionUnavailable):
        await service.select_capture(session.guild_id, 1, uuid4(), 1)

    with pytest.raises(ValueError):
        await service.select_capture(
            session.guild_id, 1, session.current_encounter.slots[0].id, 0
        )

    with pytest.raises(NotEnoughSafariBalls):
        await service.select_capture(
            session.guild_id, 1, session.current_encounter.slots[0].id, 3
        )


@pytest.mark.asyncio
async def test_confirm_without_selection_fails():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 3),))
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    with pytest.raises(SafariCaptureSelectionNotFound):
        await service.confirm_capture_selection(session.guild_id, 1)


@pytest.mark.asyncio
async def test_confirm_capture_records_balls_without_spending_and_blocks_replacement():
    activity = _TrackingActivityRepository()
    session = _published_session(
        (SafariParticipant(1, 5, 5), SafariParticipant(2, 5, 5))
    )
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 1
    )
    confirmed = await service.confirm_capture_selection(session.guild_id, 1)

    assert confirmed.state is SafariCaptureSelectionState.CONFIRMED
    assert confirmed.balls_spent == 0
    assert confirmed.balls_available == 4
    assert session.participants_by_trainer[1].remaining_balls == 5

    with pytest.raises(SafariSelectionAlreadyConfirmed):
        await service.select_capture(
            session.guild_id, 1, session.current_encounter.slots[0].id, 1
        )

    with pytest.raises(SafariSelectionAlreadyConfirmed):
        await service.confirm_capture_selection(session.guild_id, 1)

    assert session.participants_by_trainer[1].remaining_balls == 5


@pytest.mark.asyncio
async def test_declining_selection_releases_reserved_balls():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 3),))
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 2
    )
    declined = await service.decline_capture(session.guild_id, 1)

    assert declined.balls_available == 3
    assert session.participants_by_trainer[1].remaining_balls == 3


@pytest.mark.asyncio
async def test_decline_and_close_selection_transition_to_resolution():
    activity = _TrackingActivityRepository()
    session = _published_session(
        (SafariParticipant(1, 3, 3), SafariParticipant(2, 3, 3))
    )
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 1
    )
    closed = await service.close_capture_selection(session.guild_id)

    assert closed.state is SafariEncounterStatus.RESOLVING
    assert closed.confirmed_participant_ids == ()
    assert closed.declined_participant_ids == (1, 2)
    assert session.status is SafariSessionStatus.RESOLUTION


@pytest.mark.asyncio
async def test_resolve_capture_persists_creatures_candies_and_applies_session():
    activity = _TrackingActivityRepository()
    session = _published_session(
        (SafariParticipant(1, 3, 3), SafariParticipant(2, 3, 3))
    )
    await activity.save_session(session)
    transaction = _Transaction()
    service = _capture_service(activity=activity, unit_of_work=_UnitOfWork(transaction))

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 1
    )
    await service.confirm_capture_selection(session.guild_id, 1)
    await service.select_capture(
        session.guild_id, 2, session.current_encounter.slots[0].id, 1
    )
    await service.confirm_capture_selection(session.guild_id, 2)
    await service.close_capture_selection(session.guild_id)

    result = await service.resolve_capture(session.guild_id)

    events_without_activities = [
        event for event in transaction.events if event != "achievement_activity"
    ]
    assert events_without_activities == [
        "begin",
        "creature",
        "candies_get",
        "candies_save",
        "creature",
        "candies_get",
        "candies_save",
        "commit",
    ]
    assert [activity.activity_type.value for activity in transaction.activities] == [
        "capture",
        "safari_capture",
        "species_discovered",
        "capture",
        "safari_capture",
        "species_discovered",
    ]
    assert result.next_session_status is SafariSessionStatus.ROUTE_DECISION
    assert result.slot_results[0].creature is not None
    assert result.slot_results[0].collection_number == 1
    assert result.slot_results[0].creature.original_trainer_id == 1
    assert result.slot_results[0].reward.get(CandyType.ELECTRIC) == 2
    assert len(result.slot_results[0].participant_results) == 2
    assert {
        participant_result.creature.original_trainer_id
        for participant_result in result.slot_results[0].participant_results
    } == {1, 2}
    assert len(result.persisted_result.slot_results[0].captures) == 2
    assert result.rewards_by_trainer[1].get(CandyType.ELECTRIC) == 2
    assert result.rewards_by_trainer[2].get(CandyType.ELECTRIC) == 2
    assert session.current_encounter is None
    assert session.status is SafariSessionStatus.ROUTE_DECISION
    assert session.participants_by_trainer[1].captured_creature_ids == (101,)
    assert session.participants_by_trainer[2].captured_creature_ids == (102,)
    assert session.participants_by_trainer[1].remaining_balls == 2


@pytest.mark.asyncio
async def test_safari_capture_uses_the_captured_species_stage_reward():
    activity = _TrackingActivityRepository()
    session = make_session((SafariParticipant(1, 3, 3),))
    await activity.save_session(session)
    transaction = _Transaction()
    species = create_species(
        id=2,
        types=["fire"],
        evolution_species=[1, 2],
    )
    service = _capture_service(
        activity=activity,
        unit_of_work=_UnitOfWork(transaction),
        species=species,
    )
    session.publish_encounter(
        SafariEncounter(
            uuid4(),
            SafariComposition.NORMAL,
            (
                SafariEncounterSlot(
                    uuid4(),
                    OpportunityFactory.create(species),
                ),
            ),
        )
    )

    await service.select_capture(
        session.guild_id,
        1,
        session.current_encounter.slots[0].id,
        1,
    )
    await service.confirm_capture_selection(session.guild_id, 1)
    await service.close_capture_selection(session.guild_id)
    result = await service.resolve_capture(session.guild_id)

    assert result.slot_results[0].reward.get(CandyType.FIRE) == 4
    assert result.rewards_by_trainer[1].get(CandyType.FIRE) == 4


@pytest.mark.asyncio
async def test_safari_capture_records_historical_entries_inside_the_transaction():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 3),))
    await activity.save_session(session)
    transaction = _Transaction()
    entries = []

    async def record_collection_entry(creature, source):
        entries.append((creature, source))
        return True

    transaction.record_collection_entry = record_collection_entry
    service = _capture_service(activity=activity, unit_of_work=_UnitOfWork(transaction))
    slot_id = session.current_encounter.slots[0].id
    await service.select_capture(session.guild_id, 1, slot_id, 1)
    await service.confirm_capture_selection(session.guild_id, 1)
    await service.close_capture_selection(session.guild_id)

    result = await service.resolve_capture(session.guild_id)

    assert entries[0][0] is result.slot_results[0].creature
    assert entries[0][1].value == "safari"


@pytest.mark.asyncio
async def test_shared_captures_create_independent_creatures_per_participant():
    activity = _TrackingActivityRepository()
    session = _published_session(
        (
            SafariParticipant(1, 3, 3),
            SafariParticipant(2, 3, 3),
            SafariParticipant(3, 3, 3),
        )
    )
    await activity.save_session(session)
    transaction = _Transaction()
    service = _capture_service(activity=activity, unit_of_work=_UnitOfWork(transaction))
    slot_id = session.current_encounter.slots[0].id

    for trainer_id in (1, 2, 3):
        await service.select_capture(session.guild_id, trainer_id, slot_id, 1)
        await service.confirm_capture_selection(session.guild_id, trainer_id)
    await service.close_capture_selection(session.guild_id)

    base_opportunity = OpportunityFactory.create(create_species(id=25))
    generated_opportunities = tuple(
        replace(
            base_opportunity,
            ivs=IVs(index, index, index, index, index, index),
            size=Size(0.5 + index / 10),
        )
        for index in (1, 2, 3)
    )
    with patch(
        "application.safari.capture_application_service.OpportunityFactory.create",
        side_effect=generated_opportunities,
    ) as opportunity_factory:
        result = await service.resolve_capture(session.guild_id)

    creatures = [item.creature for item in result.slot_results[0].participant_results]
    assert opportunity_factory.call_count == 3
    assert len({id(creature) for creature in creatures}) == 3
    assert {creature.trainer_id for creature in creatures} == {1, 2, 3}
    assert {creature.iv_percentage for creature in creatures} == {3, 6, 10}
    assert len({creature.size.value for creature in creatures}) == 3
    assert len({creature.species.id for creature in creatures}) == 1


@pytest.mark.asyncio
async def test_resolve_capture_publishes_followup_encounter_when_segment_continues():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 3),))
    session._route_segments[0].remaining_encounters = 2
    await activity.save_session(session)
    transaction = _Transaction()
    service = _capture_service(activity=activity, unit_of_work=_UnitOfWork(transaction))

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 1
    )
    await service.confirm_capture_selection(session.guild_id, 1)
    await service.close_capture_selection(session.guild_id)

    result = await service.resolve_capture(session.guild_id)

    assert result.next_session_status is SafariSessionStatus.ENCOUNTER
    assert session.status is SafariSessionStatus.ENCOUNTER
    assert session.current_encounter is not None
    assert session.current_encounter.status is SafariEncounterStatus.OPEN
    assert len(session.current_encounter.slots) == 1
    assert session.current_segment.remaining_encounters == 1


@pytest.mark.asyncio
async def test_resolve_capture_forces_special_final_encounter_when_needed():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 3),))
    session._total_encounters = 9
    session._completed_encounter_count = 7
    session._route_segments[0].remaining_encounters = 2
    await activity.save_session(session)
    transaction = _Transaction()
    service = _capture_service(activity=activity, unit_of_work=_UnitOfWork(transaction))

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 1
    )
    await service.confirm_capture_selection(session.guild_id, 1)
    await service.close_capture_selection(session.guild_id)

    result = await service.resolve_capture(session.guild_id)

    assert result.next_session_status is SafariSessionStatus.ENCOUNTER
    assert session.status is SafariSessionStatus.ENCOUNTER
    assert session.current_encounter is not None
    assert service._encounter_generator.compositions == (SafariComposition.NORMAL,)


@pytest.mark.asyncio
async def test_resolve_capture_rolls_back_when_persistence_fails():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 3),))
    await activity.save_session(session)
    transaction = _Transaction(fail_at="creature")
    service = _capture_service(activity=activity, unit_of_work=_UnitOfWork(transaction))

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 1
    )
    await service.confirm_capture_selection(session.guild_id, 1)
    await service.close_capture_selection(session.guild_id)

    with pytest.raises(RuntimeError, match="creature"):
        await service.resolve_capture(session.guild_id)

    assert transaction.events == ["begin", "creature", "rollback"]
    assert session.status is SafariSessionStatus.RESOLUTION
    assert session.current_encounter is not None
    assert session.current_encounter.status is SafariEncounterStatus.RESOLVING
    assert activity.saved_sessions == [
        session.guild_id,
        session.guild_id,
        session.guild_id,
    ]


@pytest.mark.asyncio
async def test_concurrent_operations_for_the_same_guild_share_the_lock():
    activity = _TrackingActivityRepository()
    session = _published_session((SafariParticipant(1, 3, 3),))
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    results = await asyncio.gather(
        service.select_capture(
            session.guild_id, 1, session.current_encounter.slots[0].id, 1
        ),
        service.select_capture(
            session.guild_id, 1, session.current_encounter.slots[1].id, 1
        ),
    )

    assert all(isinstance(result, SelectSafariCaptureResult) for result in results)
    assert (
        session.current_encounter.selection_for(1).slot_id
        == session.current_encounter.slots[1].id
    )
    assert activity.saved_sessions == [
        session.guild_id,
        session.guild_id,
        session.guild_id,
    ]
