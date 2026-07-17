from dataclasses import dataclass


@dataclass(frozen=True)
class BattleFighter:
    """Prepared combatant with level-50 stats for the battle engine."""

    creature_id: int
    display_name: str
    species_showdown_id: str
    nature_showdown_id: str
    types: tuple[str, ...]
    hp_max: int
    attack: int
    special_attack: int
    defense: int
    special_defense: int
    speed: int
    move_id: str
    move_display_name: str
    pokeapi_id: int
    is_shiny: bool

    @property
    def preferred_category(self) -> str:
        return "Physical" if self.attack >= self.special_attack else "Special"
