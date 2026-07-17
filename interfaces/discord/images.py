import asyncio
from io import BytesIO

import discord
import requests

from core.creature.creature import Creature
from interfaces.discord.pokemon_mapping import get_gif_id
from rendering.gif_urls import BASE_GIF_URL, version_gif_url
from rendering.variant_assets import get_variant_gif_url

_GIF_CACHE: dict[str, bytes] = {}
_GIF_CACHE_MAX_SIZE = 100


def get_species_gif(
    species_id: int,
    shiny: bool,
) -> str:
    folder = "shiny" if shiny else "regular"

    if species_id <= 898:
        return version_gif_url(f"{BASE_GIF_URL}/gifs_pokeapi/{folder}/{species_id}.gif")

    gif_id = get_gif_id(species_id)
    return version_gif_url(f"{BASE_GIF_URL}/gifs_calidad/{folder}/{gif_id}.gif")


def get_spawn_species_gif(
    species_id: int,
    shiny: bool,
) -> str:
    folder = "shiny" if shiny else "regular"
    return version_gif_url(f"{BASE_GIF_URL}/gifs_pokeapi/{folder}/{species_id}.gif")


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
