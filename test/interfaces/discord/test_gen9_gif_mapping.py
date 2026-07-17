from interfaces.discord.images import get_spawn_species_gif, get_species_gif
from interfaces.discord.pokemon_mapping import get_gif_id
from rendering.gif_urls import GIF_ASSET_VERSION, version_gif_url
from rendering.sprites import get_capture_species_gif

BASE = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def test_gen9_gif_ids_are_unambiguous_and_correct():
    assert get_gif_id(945) == "1107"
    assert get_gif_id(950) == "1100"
    assert get_gif_id(945) != get_gif_id(950)
    assert get_gif_id(959) == "1142"


def test_gen9_regular_and_shiny_urls_use_the_mapped_ids():
    assert get_species_gif(945, False) == (
        f"{BASE}/gifs_calidad/regular/1107.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_species_gif(945, True) == (
        f"{BASE}/gifs_calidad/shiny/1107.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_species_gif(950, False) == (
        f"{BASE}/gifs_calidad/regular/1100.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_species_gif(950, True) == (
        f"{BASE}/gifs_calidad/shiny/1100.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_species_gif(945, False) != get_species_gif(950, False)
    assert get_species_gif(959, False) == (
        f"{BASE}/gifs_calidad/regular/1142.gif?v={GIF_ASSET_VERSION}"
    )


def test_spawn_and_capture_resolvers_stay_separate():
    assert get_spawn_species_gif(25, False) == (
        f"{BASE}/gifs_pokeapi/regular/25.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_spawn_species_gif(25, True) == (
        f"{BASE}/gifs_pokeapi/shiny/25.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_spawn_species_gif(906, False) == (
        f"{BASE}/gifs_pokeapi/regular/906.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_spawn_species_gif(906, True) == (
        f"{BASE}/gifs_pokeapi/shiny/906.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_capture_species_gif(25, False) == (
        f"{BASE}/regular/25.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_capture_species_gif(25, True) == (
        f"{BASE}/shiny/25.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_capture_species_gif(906, False) == (
        f"{BASE}/regular/906.gif?v={GIF_ASSET_VERSION}"
    )
    assert get_capture_species_gif(906, True) == (
        f"{BASE}/shiny/906.gif?v={GIF_ASSET_VERSION}"
    )


def test_version_helper_adds_or_replaces_query_parameters():
    assert version_gif_url(f"{BASE}/regular/25.gif") == (
        f"{BASE}/regular/25.gif?v={GIF_ASSET_VERSION}"
    )
    assert version_gif_url(f"{BASE}/regular/25.gif?foo=bar") == (
        f"{BASE}/regular/25.gif?foo=bar&v={GIF_ASSET_VERSION}"
    )
    assert (
        version_gif_url(
            f"{BASE}/regular/25.gif?foo=bar&v=old",
        )
        == f"{BASE}/regular/25.gif?foo=bar&v={GIF_ASSET_VERSION}"
    )
