from core.creature.creature import Creature

BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def get_capture_sprite(
    creature: Creature,
) -> str:
    """
    Returns the GIF used in the capture animation,
    including cosmetic variants.
    """

    if creature.current_form is not None:
        species = creature.species.name.lower()
        variant = creature.current_form.name.lower()

        return (
            f"{BASE_GIF_URL}/showdown_variantes/"
            f"{species}/"
            f"{species}-{variant}.gif"
        )

    folder = "shiny" if creature.is_shiny else "regular"

    return f"{BASE_GIF_URL}/" f"{folder}/" f"{creature.species.pokeapi_id}.gif"
