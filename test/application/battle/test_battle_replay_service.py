from application.battle.battle_replay_service import BattleReplayService
from core.battle.engine.battle_step import BattleStep, BattleStepType


def _step(step_type: BattleStepType) -> BattleStep:
    return BattleStep(
        step_type=step_type,
        side_a_name="Alice",
        side_b_name="Bob",
        message="test",
    )


def test_should_update_hp_image_on_attack_and_switch():
    service = BattleReplayService()

    assert service.should_update_hp_image(_step(BattleStepType.START))
    assert service.should_update_hp_image(_step(BattleStepType.ATTACK))
    assert service.should_update_hp_image(_step(BattleStepType.SWITCH))
    assert service.should_update_hp_image(_step(BattleStepType.VICTORY))
    assert not service.should_update_hp_image(_step(BattleStepType.MOVE))
    assert not service.should_update_hp_image(_step(BattleStepType.DAMAGE))


def test_should_update_sprite_cache_only_on_switch_events():
    service = BattleReplayService()

    assert service.should_update_sprite_cache(_step(BattleStepType.START))
    assert service.should_update_sprite_cache(_step(BattleStepType.SWITCH))
    assert service.should_update_sprite_cache(_step(BattleStepType.VICTORY))
    assert not service.should_update_sprite_cache(_step(BattleStepType.ATTACK))
