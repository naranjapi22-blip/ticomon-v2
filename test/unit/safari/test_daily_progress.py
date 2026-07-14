from datetime import date, datetime

from core.safari import (
    SafariDailyProgressService,
    SafariDailyWorld,
)


def make_world() -> SafariDailyWorld:
    return SafariDailyWorld.create(123, date(2026, 7, 14))


def test_daily_target_uses_a_minimum_of_one_active_player():
    service = SafariDailyProgressService()

    assert service.calculate_daily_target(0) == 80
    assert service.calculate_daily_target(1) == 80
    assert service.calculate_daily_target(5) == 80
    assert service.calculate_daily_target(6) == 96
    assert service.calculate_daily_target(20) == 320
    assert service.calculate_daily_target(21) == 320


def test_thresholds_use_ceil_for_fractional_targets():
    service = SafariDailyProgressService()

    assert service.calculate_thresholds(80) == (16, 32, 48, 64, 80)
    assert service.calculate_thresholds(96) == (20, 39, 58, 77, 96)
    assert service.calculate_thresholds(160) == (32, 64, 96, 128, 160)
    assert service.calculate_thresholds(320) == (64, 128, 192, 256, 320)


def test_calculate_newly_reached_levels_skips_already_unlocked_levels():
    service = SafariDailyProgressService()
    thresholds = (8, 20, 36, 56, 80)

    assert service.calculate_newly_reached_levels(0, 80, thresholds) == (
        1,
        2,
        3,
        4,
        5,
    )
    assert service.calculate_newly_reached_levels(3, 80, thresholds) == (4, 5)


def test_snapshot_reports_remaining_progress_for_zero_active_players():
    service = SafariDailyProgressService()
    world = make_world()

    snapshot = service.snapshot(world, active_player_count=0)

    assert snapshot.active_player_count == 0
    assert snapshot.effective_active_players == 5
    assert snapshot.daily_capture_target == 80
    assert snapshot.next_threshold == 16
    assert snapshot.captures_remaining == 16
    assert snapshot.all_unlocked is False


def test_snapshot_reports_progress_for_five_active_players():
    service = SafariDailyProgressService()
    world = make_world()
    world.daily_capture_count = 27
    world.daily_unlock_count = 2

    snapshot = service.snapshot(world, active_player_count=5)

    assert snapshot.active_player_count == 5
    assert snapshot.effective_active_players == 5
    assert snapshot.daily_capture_target == 80
    assert snapshot.thresholds == (16, 32, 48, 64, 80)
    assert snapshot.next_threshold == 48
    assert snapshot.captures_remaining == 21


def test_snapshot_reports_progress_for_six_and_twenty_active_players():
    service = SafariDailyProgressService()
    world = make_world()
    world.daily_capture_count = 65

    six_snapshot = service.snapshot(world, active_player_count=6)
    twenty_snapshot = service.snapshot(world, active_player_count=20)
    overflow_snapshot = service.snapshot(world, active_player_count=21)

    assert six_snapshot.daily_capture_target == 96
    assert six_snapshot.thresholds == (20, 39, 58, 77, 96)
    assert twenty_snapshot.daily_capture_target == 320
    assert twenty_snapshot.thresholds == (64, 128, 192, 256, 320)
    assert overflow_snapshot.daily_capture_target == 320
    assert overflow_snapshot.effective_active_players == 20


def test_register_capture_creates_all_crossed_unlocks_and_caps_at_five():
    service = SafariDailyProgressService()
    world = make_world()

    result = service.register_capture(
        world=world,
        species_types=["Water", "Rock"],
        captured_at=date(2026, 7, 14),
        active_player_count=5,
        progress_amount=80,
    )

    assert [unlock.level for unlock in result.created_unlocks] == [1, 2, 3, 4, 5]
    assert len(result.created_unlocks) == 5
    assert world.daily_unlock_count == 5
    assert result.snapshot.all_unlocked is True


def test_register_capture_keeps_influence_cumulative_across_unlocks():
    service = SafariDailyProgressService()
    world = make_world()

    first = service.register_capture(
        world=world,
        species_types=["Water"],
        captured_at=datetime(2026, 7, 14, 12, 0),
        active_player_count=5,
        progress_amount=16,
    )

    second = service.register_capture(
        world=world,
        species_types=["Poison"],
        captured_at=datetime(2026, 7, 14, 12, 5),
        active_player_count=5,
        progress_amount=16,
    )

    assert dict(first.created_unlocks[0].map_influence.amounts) == {"water": 1}
    assert [unlock.level for unlock in second.created_unlocks] == [2]
    assert dict(second.created_unlocks[0].map_influence.amounts) == {
        "water": 1,
        "poison": 1,
    }
    assert dict(world.current_influence.amounts) == {
        "water": 1,
        "poison": 1,
    }
    assert world.daily_unlock_count == 2


def test_existing_unlock_count_is_not_revoked_when_objective_changes():
    service = SafariDailyProgressService()
    world = make_world()
    world.daily_unlock_count = 3
    world.daily_capture_count = 30

    snapshot_before = service.snapshot(world, active_player_count=1)
    snapshot_after = service.snapshot(world, active_player_count=5)

    assert snapshot_before.daily_unlock_count == 3
    assert snapshot_after.daily_unlock_count == 3
    assert snapshot_before.daily_capture_target == 80
    assert snapshot_after.daily_capture_target == 80
    assert snapshot_before.next_threshold == 64
    assert snapshot_after.next_threshold == 64


def test_new_active_players_increase_the_target_without_reducing_unlock_count():
    service = SafariDailyProgressService()
    world = make_world()
    world.daily_unlock_count = 2
    world.daily_capture_count = 1

    result = service.register_capture(
        world=world,
        species_types=["Grass"],
        captured_at=date(2026, 7, 14),
        active_player_count=1,
        progress_amount=1,
    )

    assert result.world.daily_unlock_count == 2

    snapshot = service.snapshot(world, active_player_count=5)

    assert snapshot.daily_capture_target == 80
    assert snapshot.daily_unlock_count == 2
    assert snapshot.next_threshold == 48
