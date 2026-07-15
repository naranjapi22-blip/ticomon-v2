from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from interfaces.discord.cogs.spawn_cog import SpawnCog
from interfaces.discord.views.spawn_view import SpawnView


@pytest.mark.asyncio
async def test_spawn_sends_transparent_preview_in_standard_embed():
    session = SimpleNamespace(
        opportunities=(SimpleNamespace(species=SimpleNamespace(pokeapi_id=25)),)
    )
    core = SimpleNamespace(
        trainer_repository=SimpleNamespace(exists=AsyncMock(return_value=True)),
        energy_service=SimpleNamespace(consume=AsyncMock()),
        spawn_application=SimpleNamespace(spawn=AsyncMock(return_value=session)),
    )
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=1),
        guild=SimpleNamespace(id=2),
        send=AsyncMock(),
    )

    await SpawnCog.spawn.callback(SpawnCog(core), ctx)

    kwargs = ctx.send.await_args.kwargs
    assert isinstance(kwargs["embed"], discord.Embed)
    assert kwargs["embed"].image.url == "attachment://spawn.png"
    assert kwargs["file"].filename == "spawn.png"
    assert isinstance(kwargs["view"], SpawnView)
    assert kwargs["embed"].description == "**A wild spawn appeared!**"
