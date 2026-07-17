from dataclasses import dataclass

from core.battle.engine.battle_step import BattleStep


@dataclass(frozen=True)
class BattleResult:
    steps: tuple[BattleStep, ...]
    winner_side_name: str
    winner_trainer_id: int | None = None
