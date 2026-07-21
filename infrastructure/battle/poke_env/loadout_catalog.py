from __future__ import annotations

from functools import lru_cache

import requests
from poke_env.battle.move import Move

from core.battle.rules.move_policy import move_data_from_poke_env
from core.creature.ability import Ability, canonicalize_ability_id
from core.creature.move import CreatureMove, canonicalize_move_id
from infrastructure.battle.poke_env.showdown_species_resolver import (
    _gen9_data,
    resolve_showdown_id,
)


def _normalize_effect(effect) -> str | None:
    if not effect:
        return None
    return " ".join(str(effect).split())[:300]


@lru_cache(maxsize=512)
def _ability_effect(ability_id: str) -> str | None:
    try:
        response = requests.get(
            f"https://pokeapi.co/api/v2/ability/{ability_id}/", timeout=3
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    entries = data.get("effect_entries", ())
    english = next(
        (entry for entry in entries if entry.get("language", {}).get("name") == "en"),
        None,
    )
    if english is None:
        return None
    effect = english.get("short_effect") or english.get("effect")
    if not effect:
        return None
    return _normalize_effect(effect)


class PokeEnvLoadoutCatalog:
    """Gen 9 Showdown data used for creature loadouts and PvP validation."""

    def _showdown_id(self, species) -> str:
        return resolve_showdown_id(
            pokeapi_id=species.pokeapi_id,
            species_name=species.name,
        )

    def abilities_for(self, species) -> tuple[Ability, ...]:
        entry = _gen9_data().pokedex.get(self._showdown_id(species), {})
        raw = entry.get("abilities", {})
        result = []
        for slot, name in raw.items():
            if not name:
                continue
            if isinstance(name, dict):
                display_name = name.get("name")
                effect = _normalize_effect(
                    name.get("short_effect") or name.get("effect")
                )
            else:
                display_name = name
                effect = None
            ability_id = canonicalize_ability_id(display_name)
            result.append(
                Ability(
                    id=ability_id,
                    display_name=display_name,
                    effect=effect or _ability_effect(ability_id),
                    slot=1 if slot == "0" else 2 if slot == "1" else 3,
                    is_hidden=slot == "H",
                )
            )
        return tuple(result)

    def moves_for(self, species) -> tuple[CreatureMove, ...]:
        entry = _gen9_data().learnset.get(self._showdown_id(species), {})
        learnset = entry.get("learnset", entry)
        result = []
        for move_id in sorted(learnset):
            try:
                move = Move(move_id, gen=9)
            except Exception:
                continue
            data = move_data_from_poke_env(move_id, move)
            pp = getattr(move, "max_pp", None)
            if pp is None:
                pp = getattr(move, "pp", None)
            if pp is None:
                pp = getattr(getattr(move, "_data", None), "pp", None)
            result.append(
                CreatureMove(
                    id=canonicalize_move_id(move_id),
                    display_name=data.display_name,
                    move_type=data.move_type,
                    category=data.category,
                    base_power=data.base_power or None,
                    accuracy=data.accuracy,
                    pp=int(pp or 0),
                    priority=int(getattr(move, "priority", 0) or 0),
                )
            )
        return tuple(result)

    def initial_moves(self, species, *, seed: int | None = None) -> tuple[str, ...]:
        moves = list(self.moves_for(species))
        if not moves:
            return ()
        types = {item.lower() for item in species.types}
        scored = sorted(
            moves,
            key=lambda item: (
                item.base_power is not None and item.base_power > 0,
                item.move_type in types,
                item.category.lower() != "status",
                item.base_power or 0,
                item.id,
            ),
            reverse=True,
        )
        return tuple(item.id for item in scored[:4])
