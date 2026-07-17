from core.battle.engine.battle_step import BattleStep


class BattleNarrator:
    """Maps battle steps to player-facing narrative text."""

    @staticmethod
    def narrate(step: BattleStep) -> str:
        return step.message
