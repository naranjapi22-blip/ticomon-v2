import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from application.safari import (
    AbortSafariApplicationService,
    GetSafariActivityApplicationService,
    SafariActivityAlreadyExists,
    SafariInsufficientParticipants,
    SafariRegistrationApplicationService,
    SafariRegistrationNotFound,
    SafariUnlockUnavailable,
    StartSafariApplicationService,
)
from application.safari.activity_state import SafariActivityTracker
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SAFARI_MAX_PARTICIPANTS,
    SAFARI_MIN_PARTICIPANTS,
    SafariComposition,
    SafariEncounter,
    SafariEncounterGenerationError,
    SafariEncounterSlot,
    SafariGeneratedEncounter,
    SafariMap,
    SafariMapInfluence,
    SafariParticipantLimitReached,
    SafariRegistration,
    SafariRegistrationStatus,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariUnlock,
    SafariUnlockStatus,
    SafariWeather,
)
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from test.factories import create_species

NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)
SESSION_ID = UUID("11111111-1111-1111-1111-111111111111")


class _UnlockRepository:
    def __init__(self, unlocks=(), events=None) -> None:
        self.unlocks = list(unlocks)
        self.events = events
        self.consumed_ids: list[int] = []

    async def save(self, unlock):
        self.unlocks.append(unlock)
        return unlock

    async def get_available_by_guild_id(self, guild_id):
        return tuple(
            unlock
            for unlock in self.unlocks
            if unlock.guild_id == guild_id
            and unlock.status is SafariUnlockStatus.AVAILABLE
        )

    async def consume_next(self, guild_id, consumed_at, consumed_session_id):
        available = await self.get_available_by_guild_id(guild_id)
        if not available:
            return None
        return await self.consume(
            available[0].id,
            guild_id,
            consumed_at,
            consumed_session_id,
        )

    async def consume(
        self,
        unlock_id,
        guild_id,
        consumed_at,
        consumed_session_id,
    ):
        if self.events is not None:
            self.events.append("consume")
        for unlock in self.unlocks:
            if (
                unlock.id == unlock_id
                and unlock.guild_id == guild_id
                and unlock.status is SafariUnlockStatus.AVAILABLE
            ):
                unlock.consume(consumed_at, consumed_session_id)
                self.consumed_ids.append(unlock_id)
                return unlock
        return None


class _MapSelector:
    def __init__(self) -> None:
        self.influence = None

    def select(self, influence, random_source):
        self.influence = influence
        return SafariMap.FOREST


class _WeatherSelector:
    def select(self, safari_map, random_source):
        assert safari_map is SafariMap.FOREST
        return SafariWeather.RAIN


class _TimeSelector:
    def select(self, random_source):
        return SafariTimeOfDay.NIGHT


class _EncounterGenerator:
    def __init__(self, events=None, error=None) -> None:
        self.events = events
        self.error = error
        self.context = None

    async def generate_with_events(self, context, compositions):
        if self.events is not None:
            self.events.append("generate")
        if self.error is not None:
            raise self.error
        self.context = context
        assert compositions == (SafariComposition.NORMAL,)
        opportunity = OpportunityFactory.create(create_species(id=25))
        encounter = SafariEncounter(
            uuid4(),
            SafariComposition.NORMAL,
            (SafariEncounterSlot(uuid4(), opportunity),),
        )
        return SafariGeneratedEncounter(encounter, SafariThematicEvent.NONE)


class _TrackingActivityRepository(InMemorySafariActivityRepository):
    def __init__(self, events) -> None:
        super().__init__()
        self.events = events

    async def save_session(self, session):
        self.events.append("save_session")
        await super().save_session(session)


def _unlock(unlock_id=1, guild_id=100) -> SafariUnlock:
    return SafariUnlock(
        id=unlock_id,
        guild_id=guild_id,
        level=1,
        encounter_count=5,
        balls_per_participant=9,
        unlocked_at=NOW,
        map_influence=SafariMapInfluence({"grass": 4}),
    )


def _start_service(activity, unlocks, generator=None, events=None):
    map_selector = _MapSelector()
    return (
        StartSafariApplicationService(
            activity_repository=activity,
            unlock_repository=unlocks,
            map_selector=map_selector,
            weather_selector=_WeatherSelector(),
            time_of_day_selector=_TimeSelector(),
            encounter_generator=generator or _EncounterGenerator(events),
            random_source=object(),
            session_id_factory=lambda: SESSION_ID,
        ),
        map_selector,
    )


@pytest.mark.asyncio
async def test_open_reserves_available_unlock_without_consuming_it():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    unlock = _unlock()
    unlocks = _UnlockRepository((unlock,))
    service = SafariRegistrationApplicationService(activity, unlocks, tracker)

    result = await service.open(100, 10, NOW)

    assert result.registration.unlock_id == unlock.id
    assert result.registration.participant_ids == frozenset({10})
    assert result.capacity == SAFARI_MAX_PARTICIPANTS
    assert unlock.status is SafariUnlockStatus.AVAILABLE
    assert unlocks.consumed_ids == []


@pytest.mark.asyncio
async def test_open_requires_unlock_and_rejects_existing_activity():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    empty_service = SafariRegistrationApplicationService(
        activity,
        _UnlockRepository(),
        tracker,
    )
    with pytest.raises(SafariUnlockUnavailable):
        await empty_service.open(100, 10, NOW)

    service = SafariRegistrationApplicationService(
        activity,
        _UnlockRepository((_unlock(),)),
        tracker,
    )
    await service.open(100, 10, NOW)
    with pytest.raises(SafariActivityAlreadyExists):
        await service.open(100, 20, NOW)


@pytest.mark.asyncio
async def test_concurrent_open_creates_only_one_registration():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    service = SafariRegistrationApplicationService(
        activity,
        _UnlockRepository((_unlock(),)),
        tracker,
    )
    results = await asyncio.gather(
        service.open(100, 10, NOW),
        service.open(100, 20, NOW),
        return_exceptions=True,
    )

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert (
        sum(isinstance(result, SafariActivityAlreadyExists) for result in results) == 1
    )


@pytest.mark.asyncio
async def test_join_is_idempotent_and_enforces_global_capacity():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    unlocks = _UnlockRepository((_unlock(),))
    service = SafariRegistrationApplicationService(activity, unlocks, tracker)
    await service.open(100, 1, NOW)

    first = await service.join(100, 2)
    duplicate = await service.join(100, 2)
    for trainer_id in range(3, SAFARI_MAX_PARTICIPANTS + 1):
        await service.join(100, trainer_id)

    assert first.added
    assert not duplicate.added
    assert duplicate.participant_count == 2
    assert unlocks.consumed_ids == []
    with pytest.raises(ValueError):
        await service.join(100, SAFARI_MAX_PARTICIPANTS + 1)


@pytest.mark.asyncio
async def test_join_requires_an_open_registration():
    tracker = SafariActivityTracker()
    service = SafariRegistrationApplicationService(
        InMemorySafariActivityRepository(),
        _UnlockRepository(),
        tracker,
    )
    with pytest.raises(SafariRegistrationNotFound):
        await service.join(100, 1)


@pytest.mark.asyncio
async def test_cancel_clears_activity_and_preserves_unlock():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    unlock = _unlock()
    unlocks = _UnlockRepository((unlock,))
    service = SafariRegistrationApplicationService(activity, unlocks, tracker)
    await service.open(100, 1, NOW)

    result = await service.cancel(100)

    assert result.registration.status is SafariRegistrationStatus.CANCELLED
    assert await activity.get_activity(100) is None
    assert unlock.status is SafariUnlockStatus.AVAILABLE
    with pytest.raises(SafariRegistrationNotFound):
        await service.cancel(100)


@pytest.mark.asyncio
async def test_start_builds_complete_session_then_consumes_exact_unlock_and_stores_it():
    events = []
    activity = _TrackingActivityRepository(events)
    tracker = SafariActivityTracker()
    reserved = _unlock(2)
    other = _unlock(1)
    unlocks = _UnlockRepository((other, reserved), events)
    registration = SafariRegistration(100, 2, (20, 10), NOW)
    await activity.save_registration(registration)
    generator = _EncounterGenerator(events)
    service, map_selector = _start_service(
        activity,
        unlocks,
        generator,
        events,
    )

    result = await service.start(100, NOW)

    session = result.session
    assert events == ["generate", "consume", "save_session"]
    assert result.unlock.id == 2
    assert unlocks.consumed_ids == [2]
    assert other.status is SafariUnlockStatus.AVAILABLE
    assert registration.status is SafariRegistrationStatus.CONSUMED
    assert await activity.get_registration(100) is None
    assert await activity.get_session(100) is session
    assert session.unlock_id == 2
    assert session.level == 1
    assert session.safari_map is SafariMap.FOREST
    assert session.weather is SafariWeather.RAIN
    assert session.time_of_day is SafariTimeOfDay.NIGHT
    assert session.current_segment.remaining_encounters == 1
    assert tuple(session.participants_by_trainer) == (10, 20)
    assert all(
        participant.remaining_balls == 9
        for participant in session.participants_by_trainer.values()
    )
    assert session.current_encounter is result.generated_encounter.encounter
    assert session.current_encounter.eligible_participant_ids == frozenset({10, 20})
    assert session.current_route_vote is None
    assert all(
        not slot.opportunity.species.metadata.is_legendary
        and not slot.opportunity.species.metadata.is_mythical
        for slot in session.current_encounter.slots
    )
    assert map_selector.influence is reserved.map_influence
    assert generator.context.phase is session.phase
    assert generator.context.seen_species_ids == frozenset()
    registration_service = SafariRegistrationApplicationService(
        activity,
        unlocks,
        tracker,
    )
    with pytest.raises(SafariRegistrationNotFound):
        await registration_service.join(100, 30)


@pytest.mark.asyncio
async def test_start_requires_global_minimum_without_consuming_unlock():
    activity = InMemorySafariActivityRepository()
    unlock = _unlock()
    unlocks = _UnlockRepository((unlock,))
    await activity.save_registration(SafariRegistration(100, 1, (10,), NOW))
    service, _ = _start_service(activity, unlocks)

    assert SAFARI_MIN_PARTICIPANTS == 2
    with pytest.raises(SafariInsufficientParticipants):
        await service.start(100, NOW)
    assert unlock.status is SafariUnlockStatus.AVAILABLE
    assert await activity.get_registration(100) is not None


@pytest.mark.asyncio
async def test_start_for_testing_allows_a_single_participant():
    activity = InMemorySafariActivityRepository()
    unlock = _unlock()
    unlocks = _UnlockRepository((unlock,))
    await activity.save_registration(SafariRegistration(100, 1, (10,), NOW))
    service, _ = _start_service(activity, unlocks)

    result = await service.start_for_testing(100, NOW)

    assert result.unlock.id == unlock.id
    assert unlock.status is SafariUnlockStatus.CONSUMED
    assert await activity.get_session(100) is result.session
    assert result.session.participants_by_trainer[10].initial_balls == 9


@pytest.mark.asyncio
async def test_get_activity_snapshot_exposes_deadlines():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    registration = SafariRegistration(100, 1, (10,), NOW)
    await activity.save_registration(registration)
    tracker.set_selection_deadline(100, NOW)

    service = GetSafariActivityApplicationService(activity, tracker)
    snapshot = await service.get(100)

    assert snapshot is not None
    assert snapshot.activity is registration
    assert snapshot.timing.selection_deadline == NOW


@pytest.mark.asyncio
async def test_abort_clears_registration_and_timer_state():
    activity = InMemorySafariActivityRepository()
    tracker = SafariActivityTracker()
    registration = SafariRegistration(100, 1, (10,), NOW)
    await activity.save_registration(registration)
    tracker.set_selection_deadline(100, NOW)

    service = AbortSafariApplicationService(activity, tracker)
    result = await service.abort(100, 55)

    assert result.activity is registration
    assert await activity.get_activity(100) is None
    assert tracker.get(100).selection_deadline is None


@pytest.mark.asyncio
async def test_start_rejects_registration_above_global_capacity():
    activity = InMemorySafariActivityRepository()
    unlock = _unlock()
    unlocks = _UnlockRepository((unlock,))
    await activity.save_registration(
        SafariRegistration(100, 1, range(1, SAFARI_MAX_PARTICIPANTS + 2), NOW)
    )
    service, _ = _start_service(activity, unlocks)

    with pytest.raises(SafariParticipantLimitReached):
        await service.start(100, NOW)
    assert unlock.status is SafariUnlockStatus.AVAILABLE


@pytest.mark.asyncio
async def test_generation_failure_preserves_registration_and_unlock():
    activity = InMemorySafariActivityRepository()
    unlock = _unlock()
    unlocks = _UnlockRepository((unlock,))
    registration = SafariRegistration(100, 1, (10, 20), NOW)
    await activity.save_registration(registration)
    generator = _EncounterGenerator(
        error=SafariEncounterGenerationError("empty catalog")
    )
    service, _ = _start_service(activity, unlocks, generator)

    with pytest.raises(SafariEncounterGenerationError):
        await service.start(100, NOW)

    assert unlock.status is SafariUnlockStatus.AVAILABLE
    assert await activity.get_registration(100) is registration
    assert await activity.get_session(100) is None


@pytest.mark.asyncio
async def test_invalid_unlock_configuration_fails_before_generation_or_consumption():
    activity = InMemorySafariActivityRepository()
    unlock = _unlock()
    unlock.encounter_count = 7
    unlocks = _UnlockRepository((unlock,))
    await activity.save_registration(SafariRegistration(100, 1, (10, 20), NOW))
    generator = _EncounterGenerator()
    service, _ = _start_service(activity, unlocks, generator)

    with pytest.raises(ValueError, match="does not match"):
        await service.start(100, NOW)

    assert generator.context is None
    assert unlock.status is SafariUnlockStatus.AVAILABLE


@pytest.mark.asyncio
async def test_unavailable_unlock_at_atomic_consume_does_not_store_session():
    class _LostUnlockRepository(_UnlockRepository):
        async def consume(self, *args, **kwargs):
            return None

    activity = InMemorySafariActivityRepository()
    unlock = _unlock()
    unlocks = _LostUnlockRepository((unlock,))
    registration = SafariRegistration(100, 1, (10, 20), NOW)
    await activity.save_registration(registration)
    service, _ = _start_service(activity, unlocks)

    with pytest.raises(SafariUnlockUnavailable):
        await service.start(100, NOW)

    assert registration.status is SafariRegistrationStatus.OPEN
    assert await activity.get_registration(100) is registration
    assert await activity.get_session(100) is None


@pytest.mark.asyncio
async def test_in_memory_save_failure_occurs_after_consumption_and_is_not_rolled_back():
    class _FailingActivityRepository(InMemorySafariActivityRepository):
        async def save_session(self, session):
            raise RuntimeError("memory write failed")

    activity = _FailingActivityRepository()
    unlock = _unlock()
    unlocks = _UnlockRepository((unlock,))
    registration = SafariRegistration(100, 1, (10, 20), NOW)
    await activity.save_registration(registration)
    service, _ = _start_service(activity, unlocks)

    with pytest.raises(RuntimeError, match="memory write failed"):
        await service.start(100, NOW)

    assert unlock.status is SafariUnlockStatus.CONSUMED
    assert registration.status is SafariRegistrationStatus.OPEN
    assert await activity.get_registration(100) is registration
    assert await activity.get_session(100) is None


@pytest.mark.asyncio
async def test_concurrent_starts_create_one_session_and_consume_once():
    activity = InMemorySafariActivityRepository()
    unlocks = _UnlockRepository((_unlock(),))
    await activity.save_registration(SafariRegistration(100, 1, (10, 20), NOW))
    service, _ = _start_service(activity, unlocks)

    results = await asyncio.gather(
        service.start(100, NOW),
        service.start(100, NOW),
        return_exceptions=True,
    )

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert (
        sum(isinstance(result, SafariRegistrationNotFound) for result in results) == 1
    )
    assert unlocks.consumed_ids == [1]
    assert await activity.get_session(100) is not None
