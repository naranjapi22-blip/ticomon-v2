import asyncio
from io import BytesIO

import discord
import requests

from core.creature.creature import Creature
from interfaces.discord.mapeo_pokes import obtener_id_gif

BASE_GIF_URL = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def get_species_gif(
    species_id: int,
    shiny: bool,
) -> str:
    folder = "shiny" if shiny else "regular"

    if species_id <= 898:
        return f"{BASE_GIF_URL}/gifs_pokeapi/{folder}/{species_id}.gif"

    gif_id = obtener_id_gif(species_id)
    return f"{BASE_GIF_URL}/gifs_calidad/{folder}/{gif_id}.gif"


def get_creature_gif(
    creature: Creature,
) -> str:
    """
    Returns the GIF for a captured creature, including cosmetic variants.
    """

    if creature.current_form is not None:
        species = creature.species.name.lower()
        variant = creature.current_form.name.lower()

        return (
            f"{BASE_GIF_URL}/showdown_variantes/"
            f"{species}/"
            f"{species}-{variant}.gif"
        )

    return get_species_gif(
        species_id=creature.species.pokeapi_id,
        shiny=creature.is_shiny,
    )


def get_opportunity_gif(opportunity) -> str:

    if opportunity.initial_form is not None:
        species = opportunity.species.name.lower()
        variant = opportunity.initial_form.name.lower()

        return (
            f"{BASE_GIF_URL}/showdown_variantes/"
            f"{species}/"
            f"{species}-{variant}.gif"
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
    data = await asyncio.to_thread(
        _download_bytes,
        url,
    )

    buffer = BytesIO(data)
    buffer.seek(0)

    return discord.File(
        buffer,
        filename=filename,
    )
