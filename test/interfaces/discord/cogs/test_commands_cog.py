from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.cogs.commands_cog import CommandsCog


@pytest.mark.asyncio
async def test_commands_help_includes_trade_top_and_inventory() -> None:
    ctx = SimpleNamespace(send=AsyncMock())
    cog = CommandsCog()

    await CommandsCog.commands_command.callback(cog, ctx)

    kwargs = ctx.send.await_args.kwargs
    embed = kwargs["embed"]

    collection_field = next(
        field for field in embed.fields if field.name == "📖 Collection"
    )
    gameplay_field = next(field for field in embed.fields if field.name == "⚔️ Gameplay")

    assert "`!top [type]` — View your top Pokémon." in collection_field.value
    assert "`!inventory [type|shiny]` — View recent Pokémon." in collection_field.value
    assert (
        "`!trade @trainer <collection_number>` — "
        "Trade one Pokémon with another trainer." in gameplay_field.value
    )
