from interfaces.discord.images import get_species_gif
from interfaces.discord.pokemon_mapping import get_gif_id

BASE = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def test_gen9_gif_ids_are_unambiguous_and_correct():
    assert get_gif_id(945) == "1107"
    assert get_gif_id(950) == "1100"
    assert get_gif_id(945) != get_gif_id(950)
    assert get_gif_id(959) == "1142"


def test_gen9_regular_and_shiny_urls_use_the_mapped_ids():
    assert get_species_gif(945, False) == f"{BASE}/gifs_calidad/regular/1107.gif"
    assert get_species_gif(945, True) == f"{BASE}/gifs_calidad/shiny/1107.gif"
    assert get_species_gif(950, False) == f"{BASE}/gifs_calidad/regular/1100.gif"
    assert get_species_gif(950, True) == f"{BASE}/gifs_calidad/shiny/1100.gif"
    assert get_species_gif(945, False) != get_species_gif(950, False)
    assert get_species_gif(959, False) == f"{BASE}/gifs_calidad/regular/1142.gif"
