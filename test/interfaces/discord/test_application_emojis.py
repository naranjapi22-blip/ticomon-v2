import asyncio
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.application_emojis import (
    DEFAULT_CANDY_EMOJI,
    candy_emoji_from_index,
    clear_application_emoji_cache,
    get_candy_emoji,
    get_species_emoji,
    refresh_application_emojis,
)


class _Emoji:
    def __init__(self, name: str, emoji_id: int) -> None:
        self.name = name
        self.emoji_id = emoji_id

    def __str__(self) -> str:
        return f"<:{self.name}:{self.emoji_id}>"


class _Bot:
    def __init__(self, emojis=None, side_effect=None) -> None:
        self.fetch_application_emojis = AsyncMock(
            return_value=emojis or [],
            side_effect=side_effect,
        )


@pytest.fixture(autouse=True)
def clear_cache():
    clear_application_emoji_cache()
    yield
    clear_application_emoji_cache()


@pytest.mark.asyncio
async def test_application_emojis_are_loaded_once_and_refreshable():
    bot = _Bot([_Emoji("fire_candy", 1), _Emoji("25", 25)])

    assert await get_candy_emoji(bot, "FIRE") == "<:fire_candy:1>"
    assert await get_species_emoji(bot, 25) == "<:25:25>"
    assert bot.fetch_application_emojis.await_count == 1

    await refresh_application_emojis(bot)
    assert bot.fetch_application_emojis.await_count == 2


def test_candy_emoji_from_index_uses_empty_string_fallback():
    fire_emoji = _Emoji("fire_candy", 1)
    index = {fire_emoji.name: fire_emoji}

    assert candy_emoji_from_index(index, "fire") == str(fire_emoji)
    assert candy_emoji_from_index({}, "fire") == DEFAULT_CANDY_EMOJI
    assert candy_emoji_from_index(index, "unknown") == DEFAULT_CANDY_EMOJI
    assert candy_emoji_from_index(index, "") == DEFAULT_CANDY_EMOJI
    assert candy_emoji_from_index(index, None) == DEFAULT_CANDY_EMOJI


@pytest.mark.asyncio
async def test_application_emoji_cache_handles_missing_and_failed_lookups():
    bot = _Bot()

    assert await get_candy_emoji(bot, "water") == ""
    assert await get_species_emoji(bot, 1000) is None
    assert bot.fetch_application_emojis.await_count == 1

    failing_bot = _Bot(side_effect=RuntimeError("offline"))
    assert await get_candy_emoji(failing_bot, "fire") == ""
    assert await get_candy_emoji(failing_bot, "water") == ""
    assert failing_bot.fetch_application_emojis.await_count == 2

    failing_bot.fetch_application_emojis.side_effect = None
    failing_bot.fetch_application_emojis.return_value = [_Emoji("fire_candy", 1)]
    assert await get_candy_emoji(failing_bot, "fire") == "<:fire_candy:1>"
    assert failing_bot.fetch_application_emojis.await_count == 3


@pytest.mark.asyncio
async def test_invalid_candy_type_always_returns_empty_string():
    bot = _Bot([_Emoji("fire_candy", 1)])

    assert await get_candy_emoji(bot, None) == ""
    assert await get_candy_emoji(bot, " ") == ""


@pytest.mark.asyncio
async def test_concurrent_initial_lookups_fetch_once():
    bot = _Bot([_Emoji("1000", 1000)])

    results = await asyncio.gather(
        get_species_emoji(bot, 1000),
        get_species_emoji(bot, 1000),
    )

    assert results == ["<:1000:1000>", "<:1000:1000>"]
    assert bot.fetch_application_emojis.await_count == 1
