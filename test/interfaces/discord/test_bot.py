from unittest.mock import AsyncMock

import pytest

from interfaces.discord.bot import TicoMonBot
from interfaces.discord.cogs.trade_cog import TradeCog


@pytest.mark.asyncio
async def test_setup_hook_registers_trade_cog() -> None:
    bot = TicoMonBot()
    bot.add_cog = AsyncMock()

    await bot.setup_hook()

    assert any(
        isinstance(call.args[0], TradeCog) for call in bot.add_cog.await_args_list
    )
