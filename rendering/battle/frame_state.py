from dataclasses import dataclass


@dataclass(frozen=True)
class BattleFrameState:
    side_a_name: str
    side_b_name: str
    side_a_active_name: str
    side_b_active_name: str
    side_a_hp: int
    side_a_hp_max: int
    side_b_hp: int
    side_b_hp_max: int
    side_a_pokeapi_id: int
    side_b_pokeapi_id: int
    side_a_shiny: bool
    side_b_shiny: bool
    attack_line: str
    turn_number: int
