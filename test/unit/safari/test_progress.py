from dataclasses import FrozenInstanceError
from datetime import date, datetime
from uuid import UUID

import pytest

from core.safari import (
    SAFARI_LEVEL_CONFIGS,
    SafariMapInfluence,
    SafariUnlock,
    SafariUnlockAlreadyConsumed,
    SafariUnlockStatus,
    SafariWorld,
    SafariWorldProgressResult,
    SafariWorldProgressService,
)


def make_world() -> SafariWorld:
    return SafariWorld(
        guild_id=123,
        current_progress=0,
        daily_unlock_count=0,
        current_influence=SafariMapInfluence(),
        last_daily_reset_date=date(2026, 7, 10),
    )


def test_world_can_be_created_and_rejects_invalid_values():
    world = make_world()

    assert world.guild_id == 123
    assert world.current_progress == 0
    assert world.daily_unlock_count == 0
    assert world.current_influence.is_empty()

    with pytest.raises(ValueError):
        SafariWorld(
            guild_id=0,
            current_progress=0,
            daily_unlock_count=0,
            current_influence=SafariMapInfluence(),
            last_daily_reset_date=date(2026, 7, 10),
        )

    with pytest.raises(ValueError):
        SafariWorld(
            guild_id=1,
            current_progress=-1,
            daily_unlock_count=0,
            current_influence=SafariMapInfluence(),
            last_daily_reset_date=date(2026, 7, 10),
        )

    with pytest.raises(ValueError):
        SafariWorld(
            guild_id=1,
            current_progress=0,
            daily_unlock_count=-1,
            current_influence=SafariMapInfluence(),
            last_daily_reset_date=date(2026, 7, 10),
        )

    with pytest.raises(ValueError):
        SafariWorld(
            guild_id=1,
            current_progress=0,
            daily_unlock_count=0,
            current_influence=SafariMapInfluence(),
            last_daily_reset_date=None,  # type: ignore[arg-type]
        )


def test_world_factory_creates_empty_state_for_capture_date():
    world = SafariWorld.create(123, date(2026, 7, 13))

    assert world.guild_id == 123
    assert world.current_progress == 0
    assert world.daily_unlock_count == 0
    assert world.current_influence.is_empty()
    assert world.last_daily_reset_date == date(2026, 7, 13)


def test_capture_with_single_type_adds_progress_and_influence():
    world = make_world()
    service = SafariWorldProgressService()

    result = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
    )

    assert result.created_unlocks == ()
    assert world.current_progress == 1
    assert world.daily_unlock_count == 0
    assert dict(world.current_influence.amounts) == {"grass": 1}
    assert result.current_progress == 1
    assert result.daily_unlock_count == 0


def test_capture_with_dual_type_adds_both_types_once():
    world = make_world()
    service = SafariWorldProgressService()

    service.register_capture(
        world=world,
        species_types=["water", "poison"],
        captured_at=date(2026, 7, 10),
    )

    assert dict(world.current_influence.amounts) == {
        "water": 1,
        "poison": 1,
    }


def test_type_casing_and_spaces_are_normalized_before_deduplication():
    world = make_world()
    service = SafariWorldProgressService()

    service.register_capture(
        world=world,
        species_types=["Grass", " grass ", "GRASS"],
        captured_at=date(2026, 7, 10),
    )

    assert dict(world.current_influence.amounts) == {"grass": 1}


def test_invalid_species_types_and_progress_amount_are_rejected():
    world = make_world()
    service = SafariWorldProgressService()

    with pytest.raises(ValueError):
        service.register_capture(
            world=world,
            species_types=[],
            captured_at=date(2026, 7, 10),
        )

    with pytest.raises(ValueError):
        service.register_capture(
            world=world,
            species_types=[" "],
            captured_at=date(2026, 7, 10),
        )

    with pytest.raises(ValueError):
        service.register_capture(
            world=world,
            species_types=["grass"],
            captured_at=date(2026, 7, 10),
            progress_amount=0,
        )

    with pytest.raises(ValueError):
        service.register_capture(
            world=world,
            species_types=["grass"],
            captured_at=date(2026, 7, 10),
            progress_amount=-1,
        )


def test_unlock_creates_exactly_at_threshold_and_keeps_excess():
    world = make_world()
    service = SafariWorldProgressService()

    result = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
        progress_amount=100,
    )

    assert len(result.created_unlocks) == 1
    assert world.current_progress == 0
    assert world.daily_unlock_count == 1
    assert result.current_progress == 0
    assert result.daily_unlock_count == 1
    assert world.current_influence.is_empty()

    follow_up = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
        progress_amount=99,
    )

    assert follow_up.created_unlocks == ()
    assert world.current_progress == 99
    assert world.daily_unlock_count == 1


def test_progress_99_does_not_create_unlock_and_keeps_progress():
    world = make_world()
    service = SafariWorldProgressService()

    result = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
        progress_amount=99,
    )

    assert result.created_unlocks == ()
    assert world.current_progress == 99
    assert world.daily_unlock_count == 0


def test_progress_199_creates_one_unlock_and_keeps_99_progress():
    world = make_world()
    service = SafariWorldProgressService()

    result = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
        progress_amount=199,
    )

    assert len(result.created_unlocks) == 1
    assert world.current_progress == 99
    assert world.daily_unlock_count == 1


def test_unlock_progress_100_creates_one_and_progress_200_creates_two():
    world = make_world()
    service = SafariWorldProgressService()

    one = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
        progress_amount=100,
    )

    assert len(one.created_unlocks) == 1

    world = make_world()
    two = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
        progress_amount=200,
    )

    assert len(two.created_unlocks) == 2
    assert world.current_progress == 0
    assert world.daily_unlock_count == 2


def test_first_unlock_conserves_influence_and_later_unlocks_may_be_empty():
    world = make_world()
    world.current_influence = SafariMapInfluence({"grass": 2})
    service = SafariWorldProgressService()

    result = service.register_capture(
        world=world,
        species_types=["poison"],
        captured_at=date(2026, 7, 10),
        progress_amount=200,
    )

    assert len(result.created_unlocks) == 2
    assert dict(result.created_unlocks[0].map_influence.amounts) == {
        "grass": 2,
        "poison": 1,
    }
    assert result.created_unlocks[1].map_influence.is_empty()
    assert world.current_influence.is_empty()
    assert len(result.created_unlocks[0].map_influence.amounts) > 0


def test_unlock_level_uses_first_five_levels_and_caps_after_that():
    world = make_world()
    service = SafariWorldProgressService()

    result = service.register_capture(
        world=world,
        species_types=["grass"],
        captured_at=date(2026, 7, 10),
        progress_amount=600,
    )

    assert [unlock.level for unlock in result.created_unlocks] == [
        1,
        2,
        3,
        4,
        5,
        5,
    ]
    assert [unlock.encounter_count for unlock in result.created_unlocks] == [
        SAFARI_LEVEL_CONFIGS[1].encounter_count,
        SAFARI_LEVEL_CONFIGS[2].encounter_count,
        SAFARI_LEVEL_CONFIGS[3].encounter_count,
        SAFARI_LEVEL_CONFIGS[4].encounter_count,
        SAFARI_LEVEL_CONFIGS[5].encounter_count,
        SAFARI_LEVEL_CONFIGS[5].encounter_count,
    ]
    assert [unlock.balls_per_participant for unlock in result.created_unlocks] == [
        SAFARI_LEVEL_CONFIGS[1].balls_per_participant,
        SAFARI_LEVEL_CONFIGS[2].balls_per_participant,
        SAFARI_LEVEL_CONFIGS[3].balls_per_participant,
        SAFARI_LEVEL_CONFIGS[4].balls_per_participant,
        SAFARI_LEVEL_CONFIGS[5].balls_per_participant,
        SAFARI_LEVEL_CONFIGS[5].balls_per_participant,
    ]


def test_same_day_keeps_counter_and_new_day_resets_only_daily_counter():
    world = make_world()
    world.current_progress = 10
    world.daily_unlock_count = 3
    world.current_influence = SafariMapInfluence({"grass": 2})
    service = SafariWorldProgressService()

    same_day = service.register_capture(
        world=world,
        species_types=["water"],
        captured_at=date(2026, 7, 10),
    )

    assert world.daily_unlock_count == 3
    assert same_day.daily_unlock_count == 3
    assert world.current_progress == 11
    assert dict(world.current_influence.amounts) == {"grass": 2, "water": 1}

    next_day = service.register_capture(
        world=world,
        species_types=["poison"],
        captured_at=date(2026, 7, 11),
    )

    assert world.daily_unlock_count == 0
    assert next_day.daily_unlock_count == 0
    assert world.current_progress == 12
    assert dict(world.current_influence.amounts) == {
        "grass": 2,
        "water": 1,
        "poison": 1,
    }
    assert world.last_daily_reset_date == date(2026, 7, 11)


def test_older_capture_date_is_rejected():
    world = make_world()
    service = SafariWorldProgressService()

    with pytest.raises(ValueError):
        service.register_capture(
            world=world,
            species_types=["grass"],
            captured_at=date(2026, 7, 9),
        )


def test_unlock_can_be_consumed_once_and_preserves_configuration():
    unlock = SafariUnlock(
        id=None,
        guild_id=123,
        level=1,
        encounter_count=SAFARI_LEVEL_CONFIGS[1].encounter_count,
        balls_per_participant=SAFARI_LEVEL_CONFIGS[1].balls_per_participant,
        map_influence=SafariMapInfluence({"grass": 3}),
        unlocked_at=datetime(2026, 7, 10, 10, 0),
    )

    original_config = (
        unlock.level,
        unlock.encounter_count,
        unlock.balls_per_participant,
        dict(unlock.map_influence.amounts),
    )

    assert unlock.status == SafariUnlockStatus.AVAILABLE
    assert unlock.consumed_at is None
    assert unlock.consumed_session_id is None

    consumed_at = datetime(2026, 7, 10, 12, 0)
    session_id = UUID("11111111-1111-1111-1111-111111111111")

    unlock.consume(consumed_at=consumed_at, session_id=session_id)

    assert unlock.status == SafariUnlockStatus.CONSUMED
    assert unlock.consumed_at == consumed_at
    assert unlock.consumed_session_id == session_id
    assert (
        unlock.level,
        unlock.encounter_count,
        unlock.balls_per_participant,
        dict(unlock.map_influence.amounts),
    ) == original_config

    with pytest.raises(SafariUnlockAlreadyConsumed):
        unlock.consume(
            consumed_at=consumed_at,
            session_id=UUID("22222222-2222-2222-2222-222222222222"),
        )


def test_unlock_rejects_missing_consumption_data_and_invalid_construction():
    with pytest.raises(ValueError):
        SafariUnlock(
            id=None,
            guild_id=123,
            level=1,
            encounter_count=SAFARI_LEVEL_CONFIGS[1].encounter_count,
            balls_per_participant=SAFARI_LEVEL_CONFIGS[1].balls_per_participant,
            unlocked_at=datetime(2026, 7, 10, 9, 0),
            map_influence=SafariMapInfluence(),
            status=SafariUnlockStatus.AVAILABLE,
            consumed_at=datetime(2026, 7, 10, 10, 0),
        )

    with pytest.raises(ValueError):
        SafariUnlock(
            id=None,
            guild_id=123,
            level=1,
            encounter_count=SAFARI_LEVEL_CONFIGS[1].encounter_count,
            balls_per_participant=SAFARI_LEVEL_CONFIGS[1].balls_per_participant,
            unlocked_at=datetime(2026, 7, 10, 9, 0),
            map_influence=SafariMapInfluence(),
            status=SafariUnlockStatus.CONSUMED,
            consumed_at=None,
            consumed_session_id=UUID("11111111-1111-1111-1111-111111111111"),
        )

    with pytest.raises(ValueError):
        SafariUnlock(
            id=None,
            guild_id=0,
            level=1,
            encounter_count=SAFARI_LEVEL_CONFIGS[1].encounter_count,
            balls_per_participant=SAFARI_LEVEL_CONFIGS[1].balls_per_participant,
            map_influence=SafariMapInfluence(),
            unlocked_at=datetime(2026, 7, 10, 10, 0),
        )

    with pytest.raises(ValueError):
        SafariUnlock(
            id=None,
            guild_id=123,
            level=1,
            encounter_count=SAFARI_LEVEL_CONFIGS[1].encounter_count,
            balls_per_participant=SAFARI_LEVEL_CONFIGS[1].balls_per_participant,
            unlocked_at=None,  # type: ignore[arg-type]
            map_influence=SafariMapInfluence(),
        )


def test_progress_result_is_immutable_and_uses_tuple():
    result = SafariWorldProgressResult(
        created_unlocks=(),
        current_progress=12,
        daily_unlock_count=3,
    )

    assert isinstance(result.created_unlocks, tuple)
    assert result.current_progress == 12
    assert result.daily_unlock_count == 3

    with pytest.raises(FrozenInstanceError):
        result.current_progress = 0  # type: ignore[misc]
