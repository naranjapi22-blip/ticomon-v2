from core.creature.creature import Creature
from rendering.variant_assets import get_variant_gif_url

BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def get_capture_species_gif(
    species_id: int,
    is_shiny: bool,
) -> str:
    """Return the historical GIF collection used by CaptureAnimation."""
    folder = "shiny" if is_shiny else "regular"
    return f"{BASE_GIF_URL}/{folder}/{species_id}.gif"


def get_capture_creature_gif(
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

    return get_capture_species_gif(
        creature.species.pokeapi_id,
        creature.is_shiny,
    )


def get_capture_sprite(creature: Creature) -> str:
    """Backward-compatible name for the capture GIF resolver."""
    return get_capture_creature_gif(creature)
