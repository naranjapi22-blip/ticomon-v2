from rendering.gif_urls import BASE_GIF_URL, version_gif_url


def battle_initiator_sprite_url(pokeapi_id: int, *, shiny: bool) -> str:
    folder = "back_shiny" if shiny else "back"
    return version_gif_url(f"{BASE_GIF_URL}/{folder}/{pokeapi_id}")


def battle_opponent_sprite_url(pokeapi_id: int, *, shiny: bool) -> str:
    folder = "shiny" if shiny else "regular"
    return version_gif_url(f"{BASE_GIF_URL}/{folder}/{pokeapi_id}")
