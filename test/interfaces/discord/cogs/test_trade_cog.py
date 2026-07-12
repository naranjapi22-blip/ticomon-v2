from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from application.trade.exceptions import TradeCreatureNotOwned
from core.trade.exceptions import SameTradeParticipant
from interfaces.discord.cogs.trade_cog import TradeCog


@pytest.mark.asyncio
async def test_trade_creates_trade_and_confirms() -> None:
    create_trade = AsyncMock(
        return_value=SimpleNamespace(id=42),
    )
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            create_trade=create_trade,
        ),
    )
    cog = TradeCog(core)
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=101),
        send=AsyncMock(),
    )
    counterparty = SimpleNamespace(
        id=202,
        mention="<@202>",
    )

    await TradeCog.trade.callback(
        cog,
        ctx,
        counterparty,
        11,
        22,
    )

    create_trade.assert_awaited_once_with(
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_creature_ids=[11, 22],
        created_at=ANY,
    )
    ctx.send.assert_awaited_once_with("Trade #42 created with <@202>.")


@pytest.mark.asyncio
async def test_trade_reports_application_errors() -> None:
    create_trade = AsyncMock(
        side_effect=TradeCreatureNotOwned(101, 11),
    )
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            create_trade=create_trade,
        ),
    )
    cog = TradeCog(core)
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=101),
        send=AsyncMock(),
    )
    counterparty = SimpleNamespace(
        id=202,
        mention="<@202>",
    )

    await TradeCog.trade.callback(
        cog,
        ctx,
        counterparty,
        11,
    )

    ctx.send.assert_awaited_once_with(
        "Trade could not be created: Creature 11 is not owned by trainer 101."
    )


@pytest.mark.asyncio
async def test_trade_reports_domain_errors() -> None:
    create_trade = AsyncMock(
        side_effect=SameTradeParticipant(),
    )
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            create_trade=create_trade,
        ),
    )
    cog = TradeCog(core)
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=101),
        send=AsyncMock(),
    )
    counterparty = SimpleNamespace(
        id=101,
        mention="<@101>",
    )

    await TradeCog.trade.callback(
        cog,
        ctx,
        counterparty,
        11,
    )

    ctx.send.assert_awaited_once_with("Trade could not be created.")
