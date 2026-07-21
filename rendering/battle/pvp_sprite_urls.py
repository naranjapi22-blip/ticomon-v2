from __future__ import annotations

import re

from rendering.gif_urls import BASE_GIF_URL

_SHOWDOWN_ID_RE = re.compile(r"[^a-z0-9-]+")


def showdown_sprite_identifier(species_name: str, form_name: str | None = None) -> str:
    value = species_name
    if form_name and form_name.lower().replace("_", "-") not in species_name.lower():
        value = f"{species_name}-{form_name}"
    value = value.strip().lower().replace(" ", "-").replace("_", "-")
    return _SHOWDOWN_ID_RE.sub("", value)


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
