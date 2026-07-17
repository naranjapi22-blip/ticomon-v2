import asyncio
from collections.abc import Awaitable, Callable

from core.battle.engine.battle_step import BattleStep, BattleStepType


class BattleReplayService:
    DEFAULT_PAUSE_SECONDS = 1.5

    async def replay(
        self,
        steps: tuple[BattleStep, ...],
        callback: Callable[[BattleStep, tuple[str, ...]], Awaitable[None]],
    ) -> None:
        history: list[str] = []

        for step in steps:
            history.append(step.message)
            recent = tuple(history[-3:])
            await callback(step, recent)
            await asyncio.sleep(step.pause_seconds or self.DEFAULT_PAUSE_SECONDS)

    @staticmethod
    def should_update_hp_image(step: BattleStep) -> bool:
        return step.step_type in {
            BattleStepType.START,
            BattleStepType.ATTACK,
            BattleStepType.SWITCH,
            BattleStepType.VICTORY,
        }

    @staticmethod
    def should_update_sprite_cache(step: BattleStep) -> bool:
        return step.step_type in {
            BattleStepType.START,
            BattleStepType.SWITCH,
            BattleStepType.VICTORY,
        }
