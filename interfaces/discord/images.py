from interfaces.discord.mapeo_pokes import obtener_id_gif

BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev/gifs_calidad"


def get_species_gif(
    species_id: int,
    shiny: bool,
) -> str:
    folder = "shiny" if shiny else "regular"
    gif_id = obtener_id_gif(species_id)

    return f"{BASE_GIF_URL}/{folder}/{gif_id}.gif"
