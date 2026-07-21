from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.cogs.ivs_cog import IVsCog


@pytest.mark.asyncio
async def test_ivs_shows_ability_effect_without_mutating_ability(monkeypatch):
    nature = SimpleNamespace(arrow_for=lambda _stat: "")
    creature = SimpleNamespace(
        species=SimpleNamespace(name="Pikachu"),
        is_shiny=False,
        nature=nature,
        effective_nature=nature,
        iv_percentage=50,
        collection_number=2,
        size="Medium",
        minted_nature=None,
        iv_for=lambda _stat: 10,
    )
    ability = SimpleNamespace(
        display_name="Static", effect="May paralyze attackers on contact."
    )
    loadout = SimpleNamespace(creature=creature, ability=ability)
    ctx = SimpleNamespace(author=SimpleNamespace(id=7), send=AsyncMock())
    core = SimpleNamespace(
        creature_loadout_service=SimpleNamespace(
            get_loadout=AsyncMock(return_value=loadout)
        ),
        stat_calculator=SimpleNamespace(calculate=lambda _creature, _stat: 100),
    )
    monkeypatch.setattr(
        "interfaces.discord.cogs.ivs_cog.get_creature_gif", lambda _: ""
    )

    cog = IVsCog(core)
    await cog.ivs.callback(cog, ctx, 2)

    embed = ctx.send.await_args.kwargs["embed"]
    assert "**Ability:** Static" in embed.description
    assert "**Effect:** May paralyze attackers on contact." in embed.description
    assert ability.display_name == "Static"
