from __future__ import annotations

import random
from datetime import UTC, datetime

import pytest

from application.safari import (
    FinishSafariApplicationService,
    SafariCaptureApplicationService,
    SafariRegistrationApplicationService,
    SafariRouteApplicationService,
    StartSafariApplicationService,
)
from application.safari.activity_state import SafariActivityTracker
from core.candy.reward_policy import RewardPolicy
from core.capture.attempt_service import CaptureAttemptService
from core.capture.domain.capture_chance_calculator import CaptureChanceCalculator
from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import SafariMapInfluence, SafariUnlock
from core.safari.capture_resolution import SafariCaptureResolver
from core.safari.domain import SAFARI_LEVEL_CONFIGS, SafariSessionStatus
from core.safari.encounter_generator import SafariEncounterGenerator
from core.safari.map_selector import SafariMapSelector
from core.safari.route_option_factory import SafariRouteOptionFactory
from core.safari.time_of_day_selector import SafariTimeOfDaySelector
from core.safari.unlock import SafariUnlockStatus
from core.safari.weather_selector import SafariWeatherSelector
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from simulation.safari.runtime import (
    InMemoryCaptureUnitOfWork,
    InMemorySafariUnlockRepository,
)
from test.factories import create_species
from test.fakes.fake_species_repository import FakeSpeciesRepository


class AlwaysCaptureChanceCalculator(CaptureChanceCalculator):
    def calculate(self, opportunity, capture_ball) -> float:
        return 1.0


NOW = datetime(2026, 7, 13, 12, tzinfo=UTC)


def _species_catalog() -> tuple:
    return tuple(
        create_species(
            id=index,
            name=f"Species-{index}",
            types=["normal" if index % 2 else "water"],
        )
        for index in range(1, 13)
    )


@pytest.mark.asyncio
async def test_complete_safari_flow_in_memory():
    catalog = _species_catalog()
    species_repository = FakeSpeciesRepository(*catalog)
    activity_repository = InMemorySafariActivityRepository()
    unlock_repository = InMemorySafariUnlockRepository()
    encounter_generator = SafariEncounterGenerator(
        species_repository=species_repository,
        opportunity_factory=OpportunityFactory(),
        random_source=random.Random(42),
    )
    chance_calculator = AlwaysCaptureChanceCalculator()
    capture_resolver = SafariCaptureResolver(
        attempt_service=CaptureAttemptService(chance_calculator),
        random_source=random.Random(42),
    )
    capture_service = SafariCaptureApplicationService(
        activity_repository=activity_repository,
        capture_resolver=capture_resolver,
        unit_of_work=InMemoryCaptureUnitOfWork(),
        reward_policy=RewardPolicy(),
        creature_factory=CreatureFactory,
        encounter_generator=encounter_generator,
        random_source=random.Random(42),
    )
    registration_service = SafariRegistrationApplicationService(
        activity_repository=activity_repository,
        unlock_repository=unlock_repository,
        activity_tracker=SafariActivityTracker(),
    )
    route_service = SafariRouteApplicationService(
        activity_repository=activity_repository,
        route_option_factory=SafariRouteOptionFactory(),
        encounter_generator=encounter_generator,
        random_source=random.Random(42),
    )
    start_service = StartSafariApplicationService(
        activity_repository=activity_repository,
        unlock_repository=unlock_repository,
        map_selector=SafariMapSelector(),
        weather_selector=SafariWeatherSelector(),
        time_of_day_selector=SafariTimeOfDaySelector(),
        encounter_generator=encounter_generator,
        random_source=random.Random(42),
    )
    tracker = SafariActivityTracker()
    finish_service = FinishSafariApplicationService(
        activity_repository=activity_repository,
        activity_tracker=tracker,
        clock=lambda: NOW,
    )

    unlock = SafariUnlock(
        id=1,
        guild_id=100,
        level=1,
        encounter_count=SAFARI_LEVEL_CONFIGS[1].encounter_count,
        balls_per_participant=SAFARI_LEVEL_CONFIGS[1].balls_per_participant,
        unlocked_at=NOW,
        map_influence=SafariMapInfluence(),
    )
    await unlock_repository.save(unlock)

    await registration_service.open(100, 1, NOW)
    await registration_service.join(100, 2)
    start = await start_service.start_for_testing(100, NOW)
    assert start.unlock.status is SafariUnlockStatus.CONSUMED

    while True:
        session = await activity_repository.get_session(100)
        assert session is not None

        if session.status is SafariSessionStatus.ENCOUNTER:
            encounter = session.current_encounter
            assert encounter is not None
            slots = encounter.slots

            for index, trainer_id in enumerate(session.participants_by_trainer):
                participant = session.participants_by_trainer[trainer_id]
                if participant.remaining_balls <= 0:
                    continue
                slot = slots[min(index, len(slots) - 1)]
                balls = min(3, participant.remaining_balls)
                await capture_service.select_capture(
                    100,
                    trainer_id,
                    slot.id,
                    balls,
                )
                await capture_service.confirm_capture_selection(100, trainer_id)

            await capture_service.close_capture_selection(100)
            await capture_service.resolve_capture(100)
            continue

        if session.status is SafariSessionStatus.ROUTE_DECISION:
            vote = await route_service.open_route_vote(100, NOW)
            for trainer_id in session.participants_by_trainer:
                await route_service.cast_route_vote(
                    100,
                    trainer_id,
                    vote.options[0].id,
                )
            await route_service.resolve_route_vote(100)
            continue

        if session.status is SafariSessionStatus.FINISHED:
            break

        raise AssertionError(f"unexpected safari session status: {session.status}")

    finished = await finish_service.finish(100)
    assert (
        finished.summary.totals.encounters_completed
        == session.completed_encounter_count
    )
    assert finished.summary.totals.encounters_completed > 0
    assert finished.summary.ranking
    assert finished.summary.route.segments[0].source_option_id is None
    assert finished.summary.encounters
    assert finished.summary.totals.attempts_executed >= 0
    assert await activity_repository.get_activity(100) is None
    assert await activity_repository.get_session(100) is None
    assert tracker.get(100).selection_deadline is None
    assert tracker.get(100).route_vote_deadline is None
