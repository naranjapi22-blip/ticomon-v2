from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from application.duplicates.duplicate_result import DuplicateSpeciesResult
from interfaces.discord.application_emojis import clear_application_emoji_cache
from interfaces.discord.cogs.duplicates_cog import DuplicatesCog
from interfaces.discord.cogs.top_cog import TopCog
from interfaces.discord.views.duplicates_view import (
    DuplicatesView,
    build_duplicate_pages,
    format_duplicate_species_blocks,
)


class _Emoji:
    def __init__(self, name: str, emoji_id: int) -> None:
        self.name = name
        self.emoji_id = emoji_id

    def __str__(self) -> str:
        return f"<:{self.name}:{self.emoji_id}>"


def _bot(*emojis):
    return Mock(fetch_application_emojis=AsyncMock(return_value=list(emojis)))


def _creature(species, collection_number, iv_percentage):
    return SimpleNamespace(
        id=collection_number + 1000,
        collection_number=collection_number,
        iv_percentage=iv_percentage,
        species=species,
    )


@pytest.fixture(autouse=True)
def clear_cache():
    clear_application_emoji_cache()
    yield
    clear_application_emoji_cache()


def test_duplicate_lines_use_emoji_collection_numbers_and_iv_order():
    species = SimpleNamespace(id=819, pokeapi_id=819, name="skwovet")
    creatures = [
        _creature(species, 58, 73.12),
        _creature(species, 14, 91.40),
        _creature(species, 103, 48.92),
    ]
    emoji = _Emoji("819", 819)

    blocks = format_duplicate_species_blocks(
        species,
        creatures,
        {emoji.name: emoji},
    )

    assert blocks == ["<:819:819> Skwovet ×3 • #14 91.40% • #58 73.12% • #103 48.92%"]


def test_duplicate_lines_fallback_to_name_without_emoji():
    species = SimpleNamespace(id=197, pokeapi_id=197, name="umbreon")
    blocks = format_duplicate_species_blocks(
        species,
        [_creature(species, 27, 96.24), _creature(species, 81, 67.74)],
        {},
    )

    assert blocks == ["Umbreon ×2 • #27 96.24% • #81 67.74%"]


def test_duplicate_pages_preserve_species_blocks_and_navigation():
    blocks = [f"Species {index} ×2 • #1 99.00%" for index in range(300)]
    pages = build_duplicate_pages(blocks)
    view = DuplicatesView(7, pages)

    assert len(pages) > 1
    assert all(block in "\n\n".join(pages) for block in blocks)
    assert view.build_embed().footer.text == f"Page 1/{len(pages)}"


@pytest.mark.asyncio
async def test_duplicates_load_one_emoji_index_for_all_species():
    skwovet = SimpleNamespace(id=819, pokeapi_id=819, name="skwovet")
    umbreon = SimpleNamespace(id=197, pokeapi_id=197, name="umbreon")
    creatures = [
        _creature(skwovet, 14, 91.40),
        _creature(skwovet, 58, 73.12),
        _creature(umbreon, 27, 96.24),
        _creature(umbreon, 81, 67.74),
    ]
    bot = _bot(_Emoji("819", 819), _Emoji("197", 197))
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=7),
        bot=bot,
        send=AsyncMock(return_value=SimpleNamespace()),
    )
    core = SimpleNamespace(
        duplicate_application=SimpleNamespace(
            get_duplicates=AsyncMock(
                return_value=[
                    DuplicateSpeciesResult(819, "skwovet", 2),
                    DuplicateSpeciesResult(197, "umbreon", 2),
                ]
            )
        ),
        creature_collection_service=SimpleNamespace(
            get_top_collection=AsyncMock(return_value=creatures)
        ),
    )

    await DuplicatesCog(core).duplicates.callback(DuplicatesCog(core), ctx)

    embed = ctx.send.await_args.kwargs["embed"]
    assert "<:819:819> Skwovet ×2" in embed.description
    assert "<:197:197> Umbreon ×2" in embed.description
    assert bot.fetch_application_emojis.await_count == 1


@pytest.mark.asyncio
async def test_top_ivs_orders_by_iv_and_collection_number_and_keeps_pagination():
    pikachu = SimpleNamespace(id=25, pokeapi_id=25, name="pikachu")
    creatures = [
        _creature(pikachu, 31, 97.85),
        _creature(pikachu, 14, 98.92),
        _creature(pikachu, 27, 98.92),
    ]
    bot = _bot(_Emoji("25", 25))
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=7),
        bot=bot,
        send=AsyncMock(return_value=SimpleNamespace()),
    )
    core = SimpleNamespace(
        creature_collection_service=SimpleNamespace(
            get_top_collection=AsyncMock(return_value=creatures)
        )
    )

    await TopCog(core).top.callback(TopCog(core), ctx, "ivs")

    description = ctx.send.await_args.kwargs["embed"].description
    assert description.splitlines()[:3] == [
        "1. <:25:25> #14 Pikachu — 98.92%",
        "2. <:25:25> #27 Pikachu — 98.92%",
        "3. <:25:25> #31 Pikachu — 97.85%",
    ]
    assert ctx.send.await_args.kwargs["embed"].title == "Top Pokémon — IVs"
    assert bot.fetch_application_emojis.await_count == 1
