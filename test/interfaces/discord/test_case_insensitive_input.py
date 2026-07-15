from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from interfaces.discord.bot import TicoMonBot
from interfaces.discord.cogs.duplicates_cog import DuplicatesCog
from interfaces.discord.cogs.info import InfoCog
from interfaces.discord.cogs.inventory_cog import InventoryCog
from interfaces.discord.cogs.pokedex_cog import PokedexCog
from interfaces.discord.cogs.top_cog import TopCog
from interfaces.discord.input_normalizer import normalize_text


def _ctx():
    return SimpleNamespace(
        author=SimpleNamespace(id=99),
        send=AsyncMock(),
    )


@pytest.mark.parametrize("value", [" pikachu ", "PIKACHU", "Pikachu"])
def test_normalize_text_uses_canonical_case_and_ignores_outer_spaces(value):
    assert normalize_text(value) == "pikachu"


def test_bot_matches_commands_without_case_sensitive_aliases():
    bot = TicoMonBot()

    assert bot.case_insensitive is True


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["fire", "FIRE", "Fire", " fire "])
async def test_top_passes_canonical_type_to_core(value):
    core = SimpleNamespace(
        creature_collection_service=SimpleNamespace(
            get_top_collection=AsyncMock(return_value=[]),
        ),
    )

    await TopCog.top.callback(TopCog(core), _ctx(), value)

    core.creature_collection_service.get_top_collection.assert_awaited_once_with(
        trainer_id=99,
        pokemon_type="fire",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["shiny", "SHINY", "Shiny", " shiny "])
async def test_inventory_normalizes_shiny_filter(value):
    core = SimpleNamespace(
        creature_collection_service=SimpleNamespace(
            get_recent_collection=AsyncMock(return_value=[]),
        ),
    )

    await InventoryCog.inventory.callback(InventoryCog(core), _ctx(), value)

    core.creature_collection_service.get_recent_collection.assert_awaited_once_with(
        trainer_id=99,
        pokemon_type=None,
        shiny_only=True,
    )


@pytest.mark.asyncio
async def test_info_passes_canonical_pokemon_name_to_core():
    species = SimpleNamespace(
        name="pikachu",
        pokeapi_id=25,
        types=["electric"],
        base_stats=SimpleNamespace(for_stat=lambda _: 1),
        height=4,
        weight=60,
    )
    core = SimpleNamespace(
        species_info_service=SimpleNamespace(
            get_species_info=AsyncMock(
                return_value=SimpleNamespace(species=species, creatures=[]),
            ),
        ),
    )
    ctx = _ctx()

    with patch(
        "interfaces.discord.cogs.info.download_gif_file",
        new=AsyncMock(side_effect=RuntimeError("offline")),
    ):
        await InfoCog.info.callback(InfoCog(core), ctx, pokemon=" PIKACHU ")

    core.species_info_service.get_species_info.assert_awaited_once_with(
        trainer_id=99,
        species_name="pikachu",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["FIRE", "Fire", " fire "])
async def test_duplicates_passes_canonical_type_to_core(value):
    core = SimpleNamespace(
        duplicate_application=SimpleNamespace(
            get_duplicates_by_type=AsyncMock(return_value=[]),
        ),
    )

    await DuplicatesCog.duplicates.callback(DuplicatesCog(core), _ctx(), filtro=value)

    core.duplicate_application.get_duplicates_by_type.assert_awaited_once_with(
        trainer_id=99,
        pokemon_type="fire",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "value",
    ["CAUGHT", "Missing", "SHINY", "Legendary", "mythical"],
)
async def test_pokedex_normalizes_filters(value):
    core = SimpleNamespace()
    ctx = _ctx()
    view = AsyncMock()
    view._render_page.return_value = (None, None)

    with patch(
        "interfaces.discord.cogs.pokedex_cog.PokedexView",
        return_value=view,
    ) as view_factory:
        await PokedexCog.pokedex.callback(PokedexCog(core), ctx, value)

    filter_value = view_factory.call_args.kwargs["filter"]
    if value.casefold() == "caught":
        assert filter_value.discovered is True
    elif value.casefold() == "missing":
        assert filter_value.discovered is False
    elif value.casefold() == "legendary":
        assert filter_value.legendary is True
    elif value.casefold() == "mythical":
        assert filter_value.mythical is True
    else:
        assert filter_value is not None
