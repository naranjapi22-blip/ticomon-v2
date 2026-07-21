from __future__ import annotations

import re
from functools import lru_cache

from poke_env.data import GenData

from core.battle.species_id import to_species_showdown_id
from rendering.gif_urls import BASE_GIF_URL


@lru_cache(maxsize=1)
def _pokedex() -> dict[str, dict]:
    return GenData.from_gen(9).pokedex


def showdown_sprite_identifier(
    species_name: str,
    form_name: str | None = None,
    showdown_identifier: str | None = None,
) -> str:
    """Resolve a poke-env species identity to the PvP asset filename slug."""
    raw_identifier = showdown_identifier or species_name
    compact_identifier = to_species_showdown_id(raw_identifier)
    canonical_name = _pokedex().get(compact_identifier, {}).get("name")
    value = canonical_name or species_name
    if form_name and form_name.lower().replace("_", "-") not in value.lower():
        value = f"{value}-{form_name}"
    value = value.strip().lower().replace("_", "-")
    value = value.replace("♀", "-f").replace("♂", "-m")
    value = value.replace("'", "").replace("’", "")
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def pvp_sprite_url(
    sprite_identifier: str,
    *,
    player_side: bool,
    shiny: bool,
) -> str:
    if player_side:
        folder = "back_shiny" if shiny else "back"
    else:
        folder = "shiny" if shiny else "regular"
    return f"{BASE_GIF_URL}/PVP/{folder}/{sprite_identifier}.gif"
