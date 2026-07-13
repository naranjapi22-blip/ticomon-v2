from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.cogs.inventory_cog import InventoryCog
from interfaces.discord.cogs.top_cog import TopCog
from interfaces.discord.views.creature_list_view import CreatureListView


def _creature(
    collection_number: int,
    name: str = "Pikachu",
    iv_percentage: int = 100,
    shiny: bool = False,
):
    return SimpleNamespace(
        collection_number=collection_number,
        species=SimpleNamespace(name=name),
        iv_percentage=iv_percentage,
        is_shiny=shiny,
    )


def _ctx():
    return SimpleNamespace(
        author=SimpleNamespace(id=99),
        send=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_top_command_sends_paginated_view() -> None:
    creatures = [_creature(index, iv_percentage=100 - index) for index in range(1, 12)]
    core = SimpleNamespace(
        creature_collection_service=SimpleNamespace(
            get_top_collection=AsyncMock(return_value=creatures),
        ),
    )
    ctx = _ctx()
    cog = TopCog(core)

    await TopCog.top.callback(cog, ctx, "fire")

    kwargs = ctx.send.await_args.kwargs
    assert isinstance(kwargs["view"], CreatureListView)
    assert kwargs["embed"].title == "Top Fire Pokémon"
    assert kwargs["embed"].description.splitlines() == [
        "#1 Pikachu — IVs: 99%",
        "#2 Pikachu — IVs: 98%",
        "#3 Pikachu — IVs: 97%",
        "#4 Pikachu — IVs: 96%",
        "#5 Pikachu — IVs: 95%",
        "#6 Pikachu — IVs: 94%",
        "#7 Pikachu — IVs: 93%",
        "#8 Pikachu — IVs: 92%",
        "#9 Pikachu — IVs: 91%",
        "#10 Pikachu — IVs: 90%",
    ]
    assert kwargs["embed"].footer.text == "Page 1/2"


@pytest.mark.asyncio
async def test_inventory_command_sends_shiny_title() -> None:
    creatures = [
        _creature(8),
        _creature(7, iv_percentage=90, shiny=True),
    ]

    core = SimpleNamespace(
        creature_collection_service=SimpleNamespace(
            get_recent_collection=AsyncMock(return_value=creatures),
        ),
    )
    ctx = _ctx()
    cog = InventoryCog(core)

    await InventoryCog.inventory.callback(cog, ctx, "shiny")

    kwargs = ctx.send.await_args.kwargs
    assert isinstance(kwargs["view"], CreatureListView)
    assert kwargs["embed"].title == "✨ Recent Shiny Pokémon"
    assert kwargs["embed"].description.splitlines() == [
        "#8 Pikachu — IVs: 100%",
        "#7 Pikachu — IVs: 90%",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command", "factory", "argument", "message"),
    [
        (
            "top",
            TopCog,
            "water",
            "You do not have any Water-type Pokémon.",
        ),
        (
            "inventory",
            InventoryCog,
            "water",
            "You do not have any Water-type Pokémon.",
        ),
        (
            "inventory",
            InventoryCog,
            "shiny",
            "You do not have any shiny Pokémon.",
        ),
    ],
)
async def test_collection_commands_handle_empty_collections(
    command,
    factory,
    argument,
    message,
) -> None:
    method_name = "get_top_collection" if command == "top" else "get_recent_collection"
    core = SimpleNamespace(
        creature_collection_service=SimpleNamespace(
            **{method_name: AsyncMock(return_value=[])},
        ),
    )
    ctx = _ctx()
    cog = factory(core)

    await getattr(type(cog), command).callback(cog, ctx, argument)

    ctx.send.assert_awaited_once_with(message)


@pytest.mark.asyncio
async def test_collection_commands_report_invalid_type() -> None:
    core = SimpleNamespace(
        creature_collection_service=SimpleNamespace(
            get_top_collection=AsyncMock(
                side_effect=ValueError("Unknown Pokémon type: abc"),
            ),
        ),
    )
    ctx = _ctx()
    cog = TopCog(core)

    await TopCog.top.callback(cog, ctx, "abc")

    ctx.send.assert_awaited_once_with("Unknown Pokémon type: abc")
