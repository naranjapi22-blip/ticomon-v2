from __future__ import annotations

ACTIVITY_SPRITE_BASE_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def activity_sprite_url(
    pokeapi_id: int, *, player_side: bool, shiny: bool = False
) -> str:
    if player_side:
        folder = "back_shiny" if shiny else "back"
    else:
        folder = "shiny" if shiny else "regular"
    return f"{ACTIVITY_SPRITE_BASE_URL}/{folder}/{pokeapi_id}.gif"
