import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from core.achievement.unlock_result import AchievementUnlockResult
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_service import CaptureApplicationService
from core.capture.application.capture_unit_of_work import (
    CaptureTransaction,
    CaptureUnitOfWork,
    SaveUnlockResult,
)
from core.capture.domain.capture_attempt import CaptureAttempt
from core.capture.domain.capture_ball import CaptureBall
from core.capture.domain.capture_result import CaptureResult
from core.evolution.evolution_chain import EvolutionChain
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SafariDailyCaptureResult,
    SafariDailyProgressService,
    SafariDailyProgressSnapshot,
    SafariDailyWorld,
    SafariMapInfluence,
    SafariUnlock,
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


class _AwardService:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = []

    async def award_for_capture(self, trainer_id, species, *, is_shiny, is_safari):
        self.calls.append((trainer_id, species, is_shiny, is_safari))
        if self.fail:
            raise RuntimeError("award")
        return (AchievementUnlockResult("first_capture", CandyBundle()),)


class _Transaction(CaptureTransaction):
    def __init__(self, *, world=None, fail_at=None, events=None) -> None:
        self.daily_world = world
        self.fail_at = fail_at
        self.events = events if events is not None else []
        self.inventory = CandyInventory()
        self.saved_creature = None
        self.saved_daily_world = None
        self.saved_unlocks = []
        self.saved_unlock_results = []
        self.active_trainers: set[int] = set()
        self.activities = []

    async def save_creature(self, creature):
        self._record("creature")
        self.saved_creature = replace(creature, id=10, collection_number=4)
        return self.saved_creature

    async def get_candy_inventory(self, trainer_id):
        self._record("candies_get")
        return self.inventory

    async def save_candy_inventory(self, trainer_id, inventory):
        self._record("candies_save")

    async def record_achievement_activity(self, activity):
        self._record("achievement_activity")
        self.activities.append(activity)
        return True

    async def get_or_create_daily_world(self, guild_id, cycle_date):
        self._record("daily_world_get")
        if self.daily_world is None:
            self.daily_world = SafariDailyWorld.create(guild_id, cycle_date)
        return self.daily_world

    async def save_daily_world(self, world):
        self._record("daily_world_save")
        self.saved_daily_world = world

    async def register_daily_active_trainer_if_absent(
        self,
        guild_id,
        cycle_date,
        trainer_id,
        first_capture_at,
    ):
        self._record("daily_active_register")
        if trainer_id in self.active_trainers:
            return False
        self.active_trainers.add(trainer_id)
        return True

    async def count_daily_active_trainers(self, guild_id, cycle_date):
        self._record("daily_active_count")
        return len(self.active_trainers)

    async def expire_available_unlocks_before(self, guild_id, cycle_date):
        self._record("unlock_expire")
        return 0

    async def save_unlock(self, unlock):
        self._record("unlock")
        self.saved_unlocks.append(unlock)
        saved_unlock = replace(unlock, id=len(self.saved_unlocks))
        result = SaveUnlockResult(saved_unlock, created=True)
        self.saved_unlock_results.append(result)
        return result

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
    def register_capture(
        self,
        world,
        species_types,
        captured_at,
        *,
        active_player_count,
    ):
        world.daily_capture_count += 1
        unlocks = tuple(
            _unlock(index, map_influence=world.current_influence) for index in range(2)
        )
        snapshot = SafariDailyProgressSnapshot(
            guild_id=world.guild_id,
            cycle_date=world.cycle_date,
            active_player_count=active_player_count,
            effective_active_players=min(max(active_player_count, 5), 20),
            daily_capture_target=min(max(active_player_count, 5), 20) * 16,
            daily_capture_count=world.daily_capture_count,
            daily_unlock_count=world.daily_unlock_count,
            thresholds=(16, 32, 48, 64, 80),
            next_threshold=None,
            captures_remaining=0,
            all_unlocked=False,
            current_influence=world.current_influence,
        )
        return SafariDailyCaptureResult(
            world=world,
            snapshot=snapshot,
            created_unlocks=unlocks,
            newly_reached_levels=(1, 2),
        )


class _SingleUnlockProgressService:
    def register_capture(
        self,
        world,
        species_types,
        captured_at,
        *,
        active_player_count,
    ):
        world.daily_capture_count += 1
        world.daily_unlock_count += 1
        influence = dict(world.current_influence.amounts)
        for type_name in species_types:
            influence[type_name] = influence.get(type_name, 0) + 1
        world.current_influence = SafariMapInfluence(influence)
        unlock = _unlock(0, map_influence=world.current_influence)
        snapshot = SafariDailyProgressSnapshot(
            guild_id=world.guild_id,
            cycle_date=world.cycle_date,
            active_player_count=active_player_count,
            effective_active_players=min(max(active_player_count, 5), 20),
            daily_capture_target=min(max(active_player_count, 5), 20) * 16,
            daily_capture_count=world.daily_capture_count,
            daily_unlock_count=1,
            thresholds=(16, 32, 48, 64, 80),
            next_threshold=None,
            captures_remaining=0,
            all_unlocked=False,
            current_influence=world.current_influence,
        )
        return SafariDailyCaptureResult(
            world=world,
            snapshot=snapshot,
            created_unlocks=(unlock,),
            newly_reached_levels=(1,),
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
    assert result.creature.original_trainer_id == TRAINER_ID
    assert result.creature.collection_number == 4
    assert transaction.inventory.get_amount(CandyType.FIRE) == 1
    assert transaction.inventory.get_amount(CandyType.WATER) == 1
    assert transaction.saved_daily_world is not None
    assert transaction.saved_daily_world.guild_id == GUILD_ID
    assert transaction.saved_daily_world.daily_capture_count == 1
    assert dict(transaction.saved_daily_world.current_influence.amounts) == {
        "fire": 1,
        "water": 1,
    }
    assert transaction.saved_unlocks == []
    assert "world_get" not in transaction.events
    assert "world_save" not in transaction.events
    assert transaction.events[-2:] == ["commit", "clear"]
    assert [activity.activity_type.value for activity in transaction.activities] == [
        "capture",
        "species_discovered",
    ]
    assert await spawn.get_active(GUILD_ID) is None


@pytest.mark.asyncio
async def test_successful_capture_uses_the_captured_species_stage_reward():
    species = (
        SpeciesBuilder()
        .with_id(2)
        .with_types(["fire"])
        .with_evolution_chain(EvolutionChain(1, [1, 2], {}))
        .build()
    )
    service, transaction, _ = await _service(success=True, species=species)

    result = await service.capture(TRAINER_ID, GUILD_ID)

    assert result.reward.get(CandyType.FIRE) == 4
    assert transaction.inventory.get_amount(CandyType.FIRE) == 4


@pytest.mark.asyncio
async def test_success_records_collection_entry_inside_capture_transaction():
    service, transaction, _ = await _service(success=True)
    entries = []

    async def record_collection_entry(creature, source):
        entries.append((creature, source))
        return True

    transaction.record_collection_entry = record_collection_entry
    result = await service.capture(TRAINER_ID, GUILD_ID)

    assert entries[0][0] is result.creature
    assert entries[0][1].value == "capture"


@pytest.mark.asyncio
async def test_success_updates_existing_world_and_persists_threshold_unlock():
    world = SafariDailyWorld(
        guild_id=GUILD_ID,
        cycle_date=NOW.date(),
        daily_capture_count=1,
        daily_unlock_count=0,
        current_influence=SafariMapInfluence({"grass": 2}),
    )
    service, transaction, _ = await _service(
        success=True,
        world=world,
        progress_service=_SingleUnlockProgressService(),
    )

    await service.capture(TRAINER_ID, GUILD_ID)

    assert world.daily_capture_count == 2
    assert world.daily_unlock_count == 1
    assert len(transaction.saved_unlocks) == 1
    assert transaction.saved_unlock_results[0].created is True
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
    assert [result.created for result in transaction.saved_unlock_results] == [
        True,
        True,
    ]


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
            "achievement_activity",
            [
                "begin",
                "creature",
                "candies_get",
                "candies_save",
                "achievement_activity",
                "rollback",
            ],
        ),
        (
            "daily_world_save",
            [
                "begin",
                "creature",
                "candies_get",
                "candies_save",
                "daily_world_get",
                "unlock_expire",
                "daily_active_register",
                "daily_active_count",
                "daily_world_save",
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
                "daily_world_get",
                "unlock_expire",
                "daily_active_register",
                "daily_active_count",
                "daily_world_save",
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
    world = SafariDailyWorld(
        guild_id=GUILD_ID,
        cycle_date=NOW.date(),
        daily_capture_count=1,
        daily_unlock_count=0,
    )
    service, transaction, spawn = await _service(
        success=True,
        world=world,
        fail_at=failure,
        progress_service=(
            _SingleUnlockProgressService() if failure == "unlock" else None
        ),
    )

    with pytest.raises(RuntimeError, match=failure):
        await service.capture(TRAINER_ID, GUILD_ID)

    if failure == "achievement_activity":
        assert transaction.events == expected_events
    else:
        actual_without_activities = [
            event for event in transaction.events if event != "achievement_activity"
        ]
        assert actual_without_activities == expected_events
    assert "world_get" not in transaction.events
    assert "world_save" not in transaction.events
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


@pytest.mark.asyncio
async def test_capture_awards_after_commit_and_keeps_capture_when_award_fails():
    award_service = _AwardService(fail=True)
    service, transaction, _ = await _service(
        success=True,
        achievement_award_service=award_service,
    )

    result = await service.capture(TRAINER_ID, GUILD_ID)

    assert result.achievements == ()
    assert transaction.events[-2:] == ["commit", "clear"]
    assert len(transaction.activities) == 2
    assert len(award_service.calls) == 1


async def _service(
    *,
    success,
    world=None,
    fail_at=None,
    fail_clear=False,
    progress_service=None,
    achievement_award_service=None,
    species=None,
):
    species = species or SpeciesBuilder().with_types(["fire", "water"]).build()
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
        spawn_session_repository=spawn,
        daily_progress_service=progress_service or SafariDailyProgressService(),
        clock=lambda: NOW,
        achievement_award_service=achievement_award_service,
    )
    return service, transaction, spawn


def _unlock(index, *, map_influence=None):
    return SafariUnlock(
        id=None,
        guild_id=GUILD_ID,
        level=index + 1,
        encounter_count=5,
        balls_per_participant=9,
        unlocked_at=NOW,
        map_influence=map_influence or SafariMapInfluence(),
    )
