from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping

import discord

logger = logging.getLogger(__name__)

_CACHE: dict[object, Mapping[str, discord.Emoji]] = {}
_CACHE_LOCK = asyncio.Lock()
DEFAULT_CANDY_EMOJI = ""


async def get_application_emojis(bot) -> Mapping[str, discord.Emoji]:
    """Return the bot's application emojis, loading them at most once."""
    cached = _CACHE.get(bot)
    if cached is not None:
        return cached

    async with _CACHE_LOCK:
        cached = _CACHE.get(bot)
        if cached is not None:
            return cached

        try:
            emojis = await bot.fetch_application_emojis()
        except Exception:
            logger.warning(
                "application emoji loading failed bot_id=%s",
                getattr(bot, "application_id", None),
                exc_info=True,
            )
            return {}

        cached = {emoji.name: emoji for emoji in emojis}
        _CACHE[bot] = cached
        return cached


async def refresh_application_emojis(bot) -> None:
    async with _CACHE_LOCK:
        _CACHE.pop(bot, None)
    await get_application_emojis(bot)


async def get_candy_emoji(bot, candy_type: str) -> str:
    emojis = await get_application_emojis(bot)
    return candy_emoji_from_index(emojis, candy_type)


async def get_species_emoji(bot, pokeapi_id: int) -> str | None:
    emojis = await get_application_emojis(bot)
    return species_emoji_from_index(emojis, pokeapi_id)


def candy_emoji_from_index(
    emojis: Mapping[str, discord.Emoji],
    candy_type,
) -> str:
    type_name = getattr(candy_type, "value", candy_type)
    if not isinstance(type_name, str):
        return DEFAULT_CANDY_EMOJI
    type_name = type_name.strip().lower()
    if not type_name or not emojis:
        return DEFAULT_CANDY_EMOJI
    emoji = emojis.get(f"{type_name}_candy")
    return str(emoji) if emoji is not None else DEFAULT_CANDY_EMOJI


def candy_emoji_prefix(
    emojis: Mapping[str, discord.Emoji],
    candy_type,
) -> str:
    emoji = candy_emoji_from_index(emojis, candy_type)
    return f"{emoji} " if emoji else ""


def species_emoji_from_index(
    emojis: Mapping[str, discord.Emoji],
    pokeapi_id: int,
) -> str | None:
    emoji = emojis.get(str(pokeapi_id))
    return str(emoji) if emoji is not None else None


def species_emoji_prefix(
    emojis: Mapping[str, discord.Emoji],
    pokeapi_id: int,
) -> str:
    emoji = species_emoji_from_index(emojis, pokeapi_id)
    return f"{emoji} " if emoji else ""


def clear_application_emoji_cache() -> None:
    """Clear cached indexes; intended for isolated tests and bot lifecycle."""
    _CACHE.clear()
