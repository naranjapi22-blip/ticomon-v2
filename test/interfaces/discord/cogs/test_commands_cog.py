from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.cogs.commands_cog import CommandsCog


@pytest.mark.asyncio
async def test_commands_help_includes_safari_command() -> None:
    ctx = SimpleNamespace(send=AsyncMock())
    cog = CommandsCog()

    await CommandsCog.commands_command.callback(cog, ctx)

    kwargs = ctx.send.await_args.kwargs
    embed = kwargs["embed"]
    gameplay_field = next(field for field in embed.fields if "Gameplay" in field.name)

    assert "`!safari`" in gameplay_field.value
    assert "Start or join a Safari expedition." in gameplay_field.value
    assert "`!mint <collection_number>`" in gameplay_field.value
    assert "original nature stays intact" in gameplay_field.value
    assert "consumed only after confirming a valid change" in gameplay_field.value
