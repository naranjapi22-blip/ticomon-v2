import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
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
)
from core.capture.attempt_service import CaptureAttemptService
from core.capture.domain.capture_ball import CaptureBall
from core.safari import (
    SafariCaptureResolver,
    SafariEncounterStatus,
    SafariParticipant,
    SafariSelectionAlreadyConfirmed,
    SafariSession,
    SafariSessionStatus,
)
from core.safari.participant import NotEnoughSafariBalls
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
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


class _Transaction(CaptureTransaction):
    def __init__(self, *, fail_at: str | None = None, events: list[str] | None = None):
        self.fail_at = fail_at
        self.events = events if events is not None else []
        self._creature_counts: dict[int, int] = {}
        self._inventories: dict[int, CandyInventory] = {}
        self.saved_creatures = []
        self.saved_inventories = []

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

    async def get_or_create_world(self, guild_id, reset_date):
        raise NotImplementedError

    async def save_world(self, world):
        raise NotImplementedError

    async def save_unlock(self, unlock):
        raise NotImplementedError

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
) -> SafariCaptureApplicationService:
    if activity is None:
        activity = _TrackingActivityRepository()
    if unit_of_work is None:
        unit_of_work = _UnitOfWork(_Transaction())
    resolver = SafariCaptureResolver(
        CaptureAttemptService(_AlwaysSuccessChanceCalculator()),
        _DeterministicRandom(),
    )
    return SafariCaptureApplicationService(
        activity_repository=activity,
        capture_resolver=resolver,
        unit_of_work=unit_of_work,
        reward_policy=RewardPolicy(),
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
async def test_confirm_capture_spends_balls_once_and_blocks_replacement():
    activity = _TrackingActivityRepository()
    session = _published_session(
        (SafariParticipant(1, 3, 3), SafariParticipant(2, 3, 3))
    )
    await activity.save_session(session)
    service = _capture_service(activity=activity)

    await service.select_capture(
        session.guild_id, 1, session.current_encounter.slots[0].id, 2
    )
    confirmed = await service.confirm_capture_selection(session.guild_id, 1)

    assert confirmed.state is SafariCaptureSelectionState.CONFIRMED
    assert session.participants_by_trainer[1].remaining_balls == 1

    with pytest.raises(SafariSelectionAlreadyConfirmed):
        await service.select_capture(
            session.guild_id, 1, session.current_encounter.slots[0].id, 1
        )

    with pytest.raises(SafariSelectionAlreadyConfirmed):
        await service.confirm_capture_selection(session.guild_id, 1)

    assert session.participants_by_trainer[1].remaining_balls == 1


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
        session.guild_id, 2, session.current_encounter.slots[1].id, 1
    )
    await service.close_capture_selection(session.guild_id)

    result = await service.resolve_capture(session.guild_id)

    assert transaction.events == [
        "begin",
        "creature",
        "candies_get",
        "candies_save",
        "commit",
    ]
    assert result.next_session_status is SafariSessionStatus.ROUTE_DECISION
    assert result.slot_results[0].creature is not None
    assert result.slot_results[0].collection_number == 1
    assert result.slot_results[0].creature.original_trainer_id == 1
    assert result.slot_results[0].reward.get(CandyType.ELECTRIC) == 2
    assert result.slot_results[1].creature is None
    assert result.rewards_by_trainer[1].get(CandyType.ELECTRIC) == 2
    assert session.current_encounter is None
    assert session.status is SafariSessionStatus.ROUTE_DECISION
    assert session.participants_by_trainer[1].captured_creature_ids == (101,)


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
