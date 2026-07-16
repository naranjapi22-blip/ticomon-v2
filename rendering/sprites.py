from core.creature.creature import Creature
from rendering.variant_assets import get_variant_gif_url

BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def get_capture_sprite(
    creature: Creature,
) -> str:
    """
    Returns the GIF used in the capture animation,
    including cosmetic variants.
    """

    if creature.current_form is not None:
        return get_variant_gif_url(
            BASE_GIF_URL,
            creature.species.name,
            creature.current_form.name,
        )

    folder = "shiny" if creature.is_shiny else "regular"

    return f"{BASE_GIF_URL}/" f"{folder}/" f"{creature.species.pokeapi_id}.gif"
