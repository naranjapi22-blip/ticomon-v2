from __future__ import annotations

from dataclasses import dataclass

from core.creature.creature import Creature
from core.creature.move import canonicalize_move_id
from infrastructure.battle.poke_env.showdown_species_resolver import resolve_showdown_id

PVP_TECHNICAL_LEVEL = 50


@dataclass(frozen=True)
class PvpShowdownSet:
    species: str
    ability: str
    level: int
    evs: dict[str, int]
    ivs: dict[str, int]
    nature: str
    item: str | None
    moves: tuple[str, ...]


class PvpSetAdapter:
    def to_showdown_set(self, creature: Creature) -> PvpShowdownSet:
        if not creature.ability_id:
            raise ValueError("Creature has no persisted ability.")
        if not creature.moves or len(creature.moves) > 4:
            raise ValueError("Creature must have one to four persisted moves.")
        return PvpShowdownSet(
            species=resolve_showdown_id(
                pokeapi_id=creature.species.pokeapi_id,
                species_name=creature.species.name,
            ),
            ability=creature.ability_id,
            level=PVP_TECHNICAL_LEVEL,
            evs={stat: 0 for stat in ("hp", "atk", "def", "spa", "spd", "spe")},
            ivs={
                "hp": creature.ivs.hp,
                "atk": creature.ivs.attack,
                "def": creature.ivs.defense,
                "spa": creature.ivs.special_attack,
                "spd": creature.ivs.special_defense,
                "spe": creature.ivs.speed,
            },
            nature=creature.effective_nature.name,
            item=None,
            moves=tuple(canonicalize_move_id(move) for move in creature.moves),
        )
