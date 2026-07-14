import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application.safari import (
    SafariRouteApplicationService,
    SafariRouteVoteUnavailable,
    SafariSessionNotFound,
)
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariComposition,
    SafariEncounter,
    SafariEncounterSlot,
    SafariGeneratedEncounter,
    SafariMap,
    SafariParticipant,
    SafariPhase,
    SafariRouteOptionFactory,
    SafariRouteVoteStatus,
    SafariSession,
    SafariSessionStatus,
    SafariThematicEvent,
    SafariTimeOfDay,
    SafariWeather,
)
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from test.factories import create_species
from test.unit.safari.test_session import (
    make_segment,
    make_session,
    resolve_declined_encounter,
)

NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)


class _RouteRandom:
    def __init__(self, selected_index: int = 0) -> None:
        self.selected_index = selected_index

    def choice(self, candidates):
        if all(isinstance(candidate, int) for candidate in candidates):
            return 3 if 3 in candidates else candidates[0]
        return candidates[self.selected_index]

    def choices(self, candidates, weights, k):
        assert k == 1
        return [candidates[0]]


class _EncounterGenerator:
    def __init__(self) -> None:
        self.context = None
        self.compositions = None

    async def generate_with_events(self, context, compositions):
        self.context = context
        self.compositions = compositions
        opportunity = OpportunityFactory.create(create_species(id=25))
        encounter = SafariEncounter(
            uuid4(),
            SafariComposition.NORMAL,
            (SafariEncounterSlot(uuid4(), opportunity),),
        )
        return SafariGeneratedEncounter(encounter, SafariThematicEvent.NONE)


class _TrackingActivityRepository(InMemorySafariActivityRepository):
    def __init__(self) -> None:
        super().__init__()
        self.saved_sessions: list[int] = []

    async def save_session(self, session):
        self.saved_sessions.append(session.guild_id)
        await super().save_session(session)


def _service(
    activity: InMemorySafariActivityRepository,
    generator: _EncounterGenerator,
    random_source,
) -> SafariRouteApplicationService:
    return SafariRouteApplicationService(
        activity_repository=activity,
        route_option_factory=SafariRouteOptionFactory(),
        encounter_generator=generator,
        random_source=random_source,
    )


def _route_ready_session() -> SafariSession:
    session = make_session(
        (
            SafariParticipant(1, 9, 9),
            SafariParticipant(2, 9, 9),
            SafariParticipant(3, 9, 9),
        )
    )
    resolve_declined_encounter(session)
    return session


def _another_session(guild_id: int) -> SafariSession:
    return SafariSession(
        id=uuid4(),
        guild_id=guild_id,
        participants=(SafariParticipant(1, 9, 9),),
        total_encounters=5,
        initial_segment=make_segment(),
        started_at=NOW,
        unlock_id=1,
        level=1,
        safari_map=SafariMap.FOREST,
        weather=SafariWeather.CLEAR,
        time_of_day=SafariTimeOfDay.DAY,
    )


@pytest.mark.asyncio
async def test_open_route_vote_creates_valid_options_and_saves_session():
    activity = _TrackingActivityRepository()
    session = _route_ready_session()
    await activity.save_session(session)
    generator = _EncounterGenerator()
    service = _service(activity, generator, _RouteRandom())

    result = await service.open_route_vote(session.guild_id, NOW)

    assert result.session is session
    assert result.vote.status == SafariRouteVoteStatus.OPEN
    assert 2 <= len(result.options) <= 3
    assert activity.saved_sessions == [session.guild_id, session.guild_id]
    assert session.current_route_vote is result.vote
    assert all(
        option.source_zone == session.current_segment.zone for option in result.options
    )
    assert all(
        option.destination_zone
        in SAFARI_ZONE_DEFINITION_BY_ZONE[session.current_segment.zone].transitions
        or option.destination_zone == session.current_segment.zone
        for option in result.options
    )


@pytest.mark.asyncio
async def test_open_route_vote_rejects_when_session_is_not_ready():
    activity = InMemorySafariActivityRepository()
    session = make_session()
    await activity.save_session(session)
    service = _service(activity, _EncounterGenerator(), _RouteRandom())

    with pytest.raises(SafariRouteVoteUnavailable):
        await service.open_route_vote(session.guild_id, NOW)


@pytest.mark.asyncio
async def test_cast_route_vote_replaces_existing_vote_and_rejects_invalid_input():
    activity = _TrackingActivityRepository()
    session = _route_ready_session()
    await activity.save_session(session)
    service = _service(activity, _EncounterGenerator(), _RouteRandom())
    opened = await service.open_route_vote(session.guild_id, NOW)

    first_option = opened.options[0].id
    second_option = opened.options[1].id

    first = await service.cast_route_vote(session.guild_id, 1, first_option)
    second = await service.cast_route_vote(session.guild_id, 1, second_option)

    assert first.replaced is False
    assert second.replaced is True
    assert session.current_route_vote is opened.vote
    assert dict(opened.vote.votes_by_trainer) == {1: second_option}
    assert activity.saved_sessions[-2:] == [session.guild_id, session.guild_id]

    with pytest.raises(ValueError):
        await service.cast_route_vote(session.guild_id, 99, first_option)

    with pytest.raises(ValueError):
        await service.cast_route_vote(session.guild_id, 2, "invalid")


@pytest.mark.asyncio
async def test_resolve_route_vote_applies_destination_and_publishes_next_encounter():
    activity = _TrackingActivityRepository()
    session = _route_ready_session()
    await activity.save_session(session)
    generator = _EncounterGenerator()
    service = _service(activity, generator, _RouteRandom())
    opened = await service.open_route_vote(session.guild_id, NOW)
    selected_option = opened.options[0]
    await service.cast_route_vote(session.guild_id, 1, selected_option.id)
    await service.cast_route_vote(session.guild_id, 2, selected_option.id)

    result = await service.resolve_route_vote(session.guild_id)

    assert result.vote_result.selected_option is selected_option
    assert result.vote_result.was_tiebreak is False
    assert result.destination_segment.zone is selected_option.destination_zone
    assert session.phase == SafariPhase.DEVELOPMENT
    assert session.status == SafariSessionStatus.ENCOUNTER
    assert session.current_route_vote is None
    assert session.current_encounter is result.next_encounter.encounter
    assert generator.context is not None
    assert generator.context.safari_map is session.safari_map
    assert generator.context.weather is session.weather
    assert generator.context.time_of_day is session.time_of_day
    assert generator.context.phase is session.phase
    assert generator.context.zone is selected_option.destination_zone
    assert generator.context.seen_species_ids == session.seen_species_ids
    assert generator.context.route_allowed_events == frozenset(
        session.current_segment.allowed_events
    )
    assert activity.saved_sessions[-1] == session.guild_id


@pytest.mark.asyncio
async def test_resolve_route_vote_forces_special_final_encounter_when_needed():
    activity = _TrackingActivityRepository()
    session = _route_ready_session()
    session._total_encounters = 9
    session._completed_encounter_count = 7
    session._encounter_history = tuple()  # type: ignore[assignment]
    await activity.save_session(session)
    generator = _EncounterGenerator()
    service = _service(activity, generator, _RouteRandom())
    opened = await service.open_route_vote(session.guild_id, NOW)
    selected_option = opened.options[0]
    await service.cast_route_vote(session.guild_id, 1, selected_option.id)
    await service.cast_route_vote(session.guild_id, 2, selected_option.id)

    await service.resolve_route_vote(session.guild_id)

    assert generator.compositions == (
        SafariComposition.SOLITARY,
        SafariComposition.NORMAL,
    )


def test_resolve_route_vote_forces_special_final_encounter_for_short_safari():
    session = make_session((SafariParticipant(1, 9, 9),))
    session._total_encounters = 5
    session._completed_encounter_count = 3
    session._encounter_history = tuple()  # type: ignore[assignment]

    assert SafariRouteApplicationService._encounter_compositions_for(session) == (
        SafariComposition.SOLITARY,
        SafariComposition.NORMAL,
    )


@pytest.mark.asyncio
async def test_resolve_route_vote_keeps_normal_sequence_after_special_seen():
    activity = _TrackingActivityRepository()
    session = _route_ready_session()
    session._total_encounters = 9
    session._completed_encounter_count = 8
    session._encounter_history = [
        SimpleNamespace(
            encounter=SimpleNamespace(
                composition=SafariComposition.SOLITARY,
                is_regional_herd=False,
            )
        )
    ]
    await activity.save_session(session)
    generator = _EncounterGenerator()
    service = _service(activity, generator, _RouteRandom())
    opened = await service.open_route_vote(session.guild_id, NOW)
    selected_option = opened.options[0]
    await service.cast_route_vote(session.guild_id, 1, selected_option.id)
    await service.cast_route_vote(session.guild_id, 2, selected_option.id)

    await service.resolve_route_vote(session.guild_id)

    assert generator.compositions == (SafariComposition.NORMAL,)


@pytest.mark.asyncio
async def test_resolve_route_vote_uses_random_tiebreak_and_no_votes():
    activity = InMemorySafariActivityRepository()
    session = _route_ready_session()
    await activity.save_session(session)
    generator = _EncounterGenerator()
    service = _service(activity, generator, _RouteRandom(selected_index=1))
    opened = await service.open_route_vote(session.guild_id, NOW)

    first_option = opened.options[0]
    second_option = opened.options[1]
    await service.cast_route_vote(session.guild_id, 1, first_option.id)
    await service.cast_route_vote(session.guild_id, 2, second_option.id)

    result = await service.resolve_route_vote(session.guild_id)

    assert result.vote_result.was_tiebreak
    assert result.vote_result.selected_option is second_option

    other_session = _another_session(999)
    resolve_declined_encounter(other_session)
    await activity.save_session(other_session)
    other_service = _service(activity, _EncounterGenerator(), _RouteRandom(2))
    other_opened = await other_service.open_route_vote(other_session.guild_id, NOW)

    no_vote_result = await other_service.resolve_route_vote(other_session.guild_id)

    assert no_vote_result.vote_result.was_random_due_to_no_votes
    assert no_vote_result.vote_result.selected_option is other_opened.options[2]


@pytest.mark.asyncio
async def test_route_votes_are_isolated_by_guild():
    activity = InMemorySafariActivityRepository()
    first_session = _route_ready_session()
    second_session = _another_session(222)
    resolve_declined_encounter(second_session)
    await activity.save_session(first_session)
    await activity.save_session(second_session)
    service = _service(activity, _EncounterGenerator(), _RouteRandom())

    first_result, second_result = await asyncio.gather(
        service.open_route_vote(first_session.guild_id, NOW),
        service.open_route_vote(second_session.guild_id, NOW),
    )

    assert first_result.vote.status == SafariRouteVoteStatus.OPEN
    assert second_result.vote.status == SafariRouteVoteStatus.OPEN
    assert activity.lock(first_session.guild_id) is not activity.lock(
        second_session.guild_id
    )


@pytest.mark.asyncio
async def test_route_vote_requires_existing_session():
    service = _service(
        InMemorySafariActivityRepository(),
        _EncounterGenerator(),
        _RouteRandom(),
    )

    with pytest.raises(SafariSessionNotFound):
        await service.open_route_vote(100, NOW)

    with pytest.raises(SafariSessionNotFound):
        await service.cast_route_vote(100, 1, "x")

    with pytest.raises(SafariSessionNotFound):
        await service.resolve_route_vote(100)
