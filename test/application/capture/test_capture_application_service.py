import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_service import CaptureApplicationService
from core.capture.application.capture_unit_of_work import (
    CaptureTransaction,
    CaptureUnitOfWork,
)
from core.capture.domain.capture_attempt import CaptureAttempt
from core.capture.domain.capture_ball import CaptureBall
from core.capture.domain.capture_result import CaptureResult
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SafariMapInfluence,
    SafariUnlock,
    SafariWorld,
    SafariWorldProgressResult,
    SafariWorldProgressService,
)
from core.spawn.exceptions import NoActiveSpawnSession
from core.spawn.session import SpawnSession
from infrastructure.spawn.in_memory_spawn_session_repository import (
    InMemorySpawnSessionRepository,
)
from test.builders.creature_builder import CreatureBuilder
from test.builders.species_builder import SpeciesBuilder

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
GUILD_ID = 55
TRAINER_ID = 77


class _CaptureService:
    def __init__(self, result: CaptureResult) -> None:
        self.result = result

    def capture(self, trainer_id, opportunity):
        return self.result


class _Transaction(CaptureTransaction):
    def __init__(self, *, world=None, fail_at=None, events=None) -> None:
        self.world = world
        self.fail_at = fail_at
        self.events = events if events is not None else []
        self.inventory = CandyInventory()
        self.saved_creature = None
        self.saved_world = None
        self.saved_unlocks = []

    async def save_creature(self, creature):
        self._record("creature")
        self.saved_creature = replace(creature, id=10, collection_number=4)
        return self.saved_creature

    async def get_candy_inventory(self, trainer_id):
        self._record("candies_get")
        return self.inventory

    async def save_candy_inventory(self, trainer_id, inventory):
        self._record("candies_save")

    async def get_or_create_world(self, guild_id, reset_date):
        self._record("world_get")
        if self.world is None:
            self.world = SafariWorld.create(guild_id, reset_date)
        return self.world

    async def save_world(self, world):
        self._record("world_save")
        self.saved_world = world
        return world

    async def save_unlock(self, unlock):
        self._record("unlock")
        self.saved_unlocks.append(unlock)
        return replace(unlock, id=len(self.saved_unlocks))

    def _record(self, operation):
        self.events.append(operation)
        if self.fail_at == operation:
            raise RuntimeError(operation)


class _UnitOfWork(CaptureUnitOfWork):
    def __init__(self, transaction: _Transaction) -> None:
        self.capture_transaction = transaction
        self.events = transaction.events

    @asynccontextmanager
    async def transaction(self):
        self.events.append("begin")
        try:
            yield self.capture_transaction
        except Exception:
            self.events.append("rollback")
            raise
        else:
            self.events.append("commit")


class _SpawnRepository(InMemorySpawnSessionRepository):
    def __init__(self, events, *, fail_clear=False) -> None:
        super().__init__()
        self.events = events
        self.fail_clear = fail_clear

    async def clear(self, guild_id):
        self.events.append("clear")
        if self.fail_clear:
            raise RuntimeError("clear")
        await super().clear(guild_id)


class _MultipleUnlockProgressService:
    def register_capture(self, world, species_types, captured_at):
        world.current_progress += 1
        unlocks = tuple(_unlock(index) for index in range(2))
        return SafariWorldProgressResult(
            created_unlocks=unlocks,
            current_progress=world.current_progress,
            daily_unlock_count=world.daily_unlock_count,
        )


@pytest.mark.asyncio
async def test_failed_capture_writes_nothing_and_keeps_spawn_active():
    service, transaction, spawn = await _service(success=False)

    result = await service.capture(TRAINER_ID, GUILD_ID)

    assert result.success is False
    assert transaction.events == []
    assert await spawn.get_active(GUILD_ID) is not None


@pytest.mark.asyncio
async def test_success_persists_creature_candies_and_creates_world():
    service, transaction, spawn = await _service(success=True)

    result = await service.capture(TRAINER_ID, GUILD_ID)

    assert result.success is True
    assert result.creature is transaction.saved_creature
    assert result.creature.collection_number == 4
    assert transaction.inventory.get_amount(CandyType.FIRE) == 1
    assert transaction.inventory.get_amount(CandyType.WATER) == 1
    assert transaction.saved_world is not None
    assert transaction.saved_world.guild_id == GUILD_ID
    assert transaction.saved_world.current_progress == 1
    assert dict(transaction.saved_world.current_influence.amounts) == {
        "fire": 1,
        "water": 1,
    }
    assert transaction.saved_unlocks == []
    assert transaction.events[-2:] == ["commit", "clear"]
    assert await spawn.get_active(GUILD_ID) is None


@pytest.mark.asyncio
async def test_success_updates_existing_world_and_persists_threshold_unlock():
    world = SafariWorld(
        guild_id=GUILD_ID,
        current_progress=99,
        daily_unlock_count=0,
        current_influence=SafariMapInfluence({"grass": 2}),
        last_daily_reset_date=NOW.date(),
    )
    service, transaction, _ = await _service(success=True, world=world)

    await service.capture(TRAINER_ID, GUILD_ID)

    assert world.current_progress == 0
    assert world.daily_unlock_count == 1
    assert len(transaction.saved_unlocks) == 1
    assert dict(transaction.saved_unlocks[0].map_influence.amounts) == {
        "grass": 2,
        "fire": 1,
        "water": 1,
    }


@pytest.mark.asyncio
async def test_all_unlocks_from_progress_result_are_saved_in_order():
    service, transaction, _ = await _service(
        success=True,
        progress_service=_MultipleUnlockProgressService(),
    )

    await service.capture(TRAINER_ID, GUILD_ID)

    assert [unlock.level for unlock in transaction.saved_unlocks] == [1, 2]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,expected_events",
    [
        ("creature", ["begin", "creature", "rollback"]),
        (
            "candies_save",
            ["begin", "creature", "candies_get", "candies_save", "rollback"],
        ),
        (
            "world_save",
            [
                "begin",
                "creature",
                "candies_get",
                "candies_save",
                "world_get",
                "world_save",
                "rollback",
            ],
        ),
        (
            "unlock",
            [
                "begin",
                "creature",
                "candies_get",
                "candies_save",
                "world_get",
                "world_save",
                "unlock",
                "rollback",
            ],
        ),
    ],
)
async def test_persistence_failure_rolls_back_and_keeps_spawn(
    failure,
    expected_events,
):
    world = SafariWorld(
        guild_id=GUILD_ID,
        current_progress=99,
        daily_unlock_count=0,
        last_daily_reset_date=NOW.date(),
    )
    service, transaction, spawn = await _service(
        success=True,
        world=world,
        fail_at=failure,
    )

    with pytest.raises(RuntimeError, match=failure):
        await service.capture(TRAINER_ID, GUILD_ID)

    assert transaction.events == expected_events
    assert "clear" not in transaction.events
    assert await spawn.get_active(GUILD_ID) is not None


@pytest.mark.asyncio
async def test_clear_occurs_after_commit_and_failure_does_not_undo_commit():
    service, transaction, spawn = await _service(success=True, fail_clear=True)

    with pytest.raises(RuntimeError, match="clear"):
        await service.capture(TRAINER_ID, GUILD_ID)

    assert transaction.events[-2:] == ["commit", "clear"]
    assert await spawn.get_active(GUILD_ID) is not None


@pytest.mark.asyncio
async def test_concurrent_double_click_persists_only_one_capture():
    service, transaction, spawn = await _service(success=True)

    results = await asyncio.gather(
        service.capture(TRAINER_ID, GUILD_ID),
        service.capture(TRAINER_ID, GUILD_ID),
        return_exceptions=True,
    )

    assert sum(not isinstance(result, Exception) for result in results) == 1
    assert sum(isinstance(result, NoActiveSpawnSession) for result in results) == 1
    assert transaction.events.count("begin") == 1
    assert transaction.events.count("creature") == 1
    assert await spawn.get_active(GUILD_ID) is None


async def _service(
    *,
    success,
    world=None,
    fail_at=None,
    fail_clear=False,
    progress_service=None,
):
    species = SpeciesBuilder().with_types(["fire", "water"]).build()
    opportunity = OpportunityFactory.create(species)
    creature = (
        CreatureBuilder().with_species(species).with_trainer_id(TRAINER_ID).build()
    )
    attempt = CaptureAttempt(opportunity, CaptureBall.GREAT_BALL, 0.5)
    capture_result = CaptureResult(
        attempt=attempt,
        success=success,
        creature=creature if success else None,
    )
    events = []
    transaction = _Transaction(world=world, fail_at=fail_at, events=events)
    unit_of_work = _UnitOfWork(transaction)
    spawn = _SpawnRepository(events, fail_clear=fail_clear)
    await spawn.save(
        GUILD_ID,
        SpawnSession(
            owner_id=TRAINER_ID,
            opportunities=[opportunity],
            selected_opportunity=opportunity,
        ),
    )
    service = CaptureApplicationService(
        capture_service=_CaptureService(capture_result),
        unit_of_work=unit_of_work,
        reward_policy=RewardPolicy(),
        world_progress_service=progress_service or SafariWorldProgressService(),
        spawn_session_repository=spawn,
        clock=lambda: NOW,
    )
    return service, transaction, spawn


def _unlock(index):
    return SafariUnlock(
        id=None,
        guild_id=GUILD_ID,
        level=index + 1,
        encounter_count=5,
        balls_per_participant=9,
        unlocked_at=NOW,
    )
