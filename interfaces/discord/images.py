import asyncio
from io import BytesIO

import discord
import requests

from core.creature.creature import Creature
from interfaces.discord.pokemon_mapping import get_gif_id
from rendering.variant_assets import get_variant_gif_url

BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"

_GIF_CACHE: dict[str, bytes] = {}
_GIF_CACHE_MAX_SIZE = 100

_SPAWN_HISTORICAL_MISSING_REGULAR = frozenset({1015})
_SPAWN_HISTORICAL_MISSING_SHINY = frozenset(
    {
        29,
        32,
        785,
        786,
        787,
        788,
        990,
        991,
        992,
        993,
        994,
        995,
        1001,
        1002,
        1003,
        1004,
        1006,
        1008,
        1010,
        1014,
        1015,
        1016,
        1017,
        1022,
        1023,
        1024,
    }
)


def get_species_gif(
    species_id: int,
    shiny: bool,
) -> str:
    folder = "shiny" if shiny else "regular"

    if species_id <= 898:
        return f"{BASE_GIF_URL}/gifs_pokeapi/{folder}/{species_id}.gif"

    gif_id = get_gif_id(species_id)
    return f"{BASE_GIF_URL}/gifs_calidad/{folder}/{gif_id}.gif"


def get_spawn_species_gif(
    species_id: int,
    shiny: bool,
) -> str:
    """
    Returns the historical GIF used by Spawn, with a static fallback for
    species missing from the historical collection.
    """

    folder = "shiny" if shiny else "regular"
    missing = (
        _SPAWN_HISTORICAL_MISSING_SHINY if shiny else _SPAWN_HISTORICAL_MISSING_REGULAR
    )

    if species_id in missing:
        return get_species_gif(species_id, shiny)

    return f"{BASE_GIF_URL}/{folder}/{species_id}.gif"


def get_creature_gif(
    creature: Creature,
) -> str:
    """
    Returns the GIF for a captured creature, including cosmetic variants.
    """

    if creature.current_form is not None:
        return get_variant_gif_url(
            BASE_GIF_URL,
            creature.species.name,
            creature.current_form.name,
        )

    return get_species_gif(
        species_id=creature.species.pokeapi_id,
        shiny=creature.is_shiny,
    )


def get_opportunity_gif(opportunity) -> str:

    if opportunity.initial_form is not None:
        return get_variant_gif_url(
            BASE_GIF_URL,
            opportunity.species.name,
            opportunity.initial_form.name,
        )

    return get_species_gif(
        species_id=opportunity.species.pokeapi_id,
        shiny=opportunity.is_shiny,
    )


def _download_bytes(url: str) -> bytes:
    with requests.get(
        url,
        timeout=10,
        stream=True,
    ) as response:
        response.raise_for_status()
        return response.content


async def download_gif_file(
    url: str,
    filename: str,
) -> discord.File:
    data = _GIF_CACHE.get(url)

    if data is None:
        data = await asyncio.to_thread(
            _download_bytes,
            url,
        )

        if len(_GIF_CACHE) >= _GIF_CACHE_MAX_SIZE:
            _GIF_CACHE.pop(next(iter(_GIF_CACHE)))

        _GIF_CACHE[url] = data

    buffer = BytesIO(data)
    buffer.seek(0)

    return discord.File(
        buffer,
        filename=filename,
    )
