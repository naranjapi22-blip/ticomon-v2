from application.battle.battle_dto import BattleDisplayDTO
from core.battle.battle import Battle
from core.battle.engine.battle_step import BattleStep
from rendering.battle.frame_state import BattleFrameState


class BattleDisplayService:
    def to_display_dto(self, battle: Battle) -> BattleDisplayDTO:
        return BattleDisplayDTO(
            battle_id=battle.id or 0,
            initiator_trainer_id=battle.initiator_trainer_id,
            opponent_trainer_id=battle.opponent_trainer_id,
            status=battle.status.value,
            initiator_has_party=battle.has_party(battle.initiator_trainer_id),
            opponent_has_party=battle.has_party(battle.opponent_trainer_id),
            winner_trainer_id=battle.winner_trainer_id,
        )

    def frame_from_step(
        self,
        step: BattleStep,
        *,
        side_a_pokeapi_id: int,
        side_b_pokeapi_id: int,
        side_a_shiny: bool,
        side_b_shiny: bool,
        turn_number: int,
        side_a_display_name: str | None = None,
        side_b_display_name: str | None = None,
    ) -> BattleFrameState:
        side_a = step.state_snapshot.get(step.side_a_name, {})
        side_b = step.state_snapshot.get(step.side_b_name, {})

        side_a_hp = side_a.get("hp", [0])
        side_b_hp = side_b.get("hp", [0])
        side_a_hp_max = side_a.get("hp_max", [1])
        side_b_hp_max = side_b.get("hp_max", [1])
        side_a_index = side_a.get("active_index", 0)
        side_b_index = side_b.get("active_index", 0)

        return BattleFrameState(
            side_a_name=side_a_display_name or step.side_a_name,
            side_b_name=side_b_display_name or step.side_b_name,
            side_a_active_name=side_a.get("active_name", "???"),
            side_b_active_name=side_b.get("active_name", "???"),
            side_a_hp=side_a_hp[side_a_index] if side_a_hp else 0,
            side_a_hp_max=side_a_hp_max[side_a_index] if side_a_hp_max else 1,
            side_b_hp=side_b_hp[side_b_index] if side_b_hp else 0,
            side_b_hp_max=side_b_hp_max[side_b_index] if side_b_hp_max else 1,
            side_a_pokeapi_id=side_a_pokeapi_id,
            side_b_pokeapi_id=side_b_pokeapi_id,
            side_a_shiny=side_a_shiny,
            side_b_shiny=side_b_shiny,
            attack_line=step.message,
            turn_number=turn_number,
        )
