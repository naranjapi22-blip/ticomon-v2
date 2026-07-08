BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def get_capture_sprite(
    species_id: int,
    shiny: bool,
) -> str:
    folder = "shiny" if shiny else "regular"

    return f"{BASE_GIF_URL}/{folder}/{species_id}.gif"
