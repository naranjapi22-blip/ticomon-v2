import inspect
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest
from discord.ext import commands

from application.trade.exceptions import TradeCreatureNotOwned
from application.trade.trade_display import (
    TradeCreatureDisplay,
    TradeDisplay,
    TradeOfferDisplay,
)
from core.trade.exceptions import SameTradeParticipant
from core.trade.trade import Trade
from core.trade.trade_offer import TradeOffer
from core.trade.trade_status import TradeStatus
from interfaces.discord.cogs.trade_cog import TradeCog
from interfaces.discord.views.trade_view import TradeView


def _trade() -> Trade:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return Trade._reconstitute(
        trade_id=42,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOffer.create(101, 11),
        counterparty_offer=None,
        created_at=created_at,
        expires_at=None,
        status=TradeStatus.OPEN,
        initiator_accepted_at=None,
        counterparty_accepted_at=None,
    )


def _trade_display() -> TradeDisplay:
    creature = TradeCreatureDisplay(
        creature_id=11,
        trainer_id=101,
        species_name="Pikachu",
        collection_number=7,
        iv_percentage=100,
        is_shiny=False,
        nature="Hardy",
        size="M (1.00×)",
        current_form_name=None,
    )

    return TradeDisplay(
        trade_id=42,
        status=TradeStatus.OPEN,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOfferDisplay(
            trainer_id=101,
            creature=creature,
            accepted_at=None,
        ),
        counterparty_offer=None,
        completed_at=None,
        cancelled_by_trainer_id=None,
        rejected_by_trainer_id=None,
    )


@pytest.mark.asyncio
async def test_trade_creates_trade_and_opens_view() -> None:
    trade = _trade()
    trade_display = _trade_display()
    create_trade = AsyncMock(return_value=trade)
    get_trade_display = AsyncMock(return_value=trade_display)
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            create_trade_from_collection_number=create_trade,
        ),
        trade_display_service=SimpleNamespace(
            get_trade_display=get_trade_display,
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

    create_trade.assert_awaited_once_with(
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_collection_number=11,
        created_at=ANY,
    )
    get_trade_display.assert_awaited_once_with(42)
    ctx.send.assert_awaited_once()
    kwargs = ctx.send.await_args.kwargs
    assert isinstance(kwargs["view"], TradeView)
    assert kwargs["embed"].title == "⚖️ Trade #42"


@pytest.mark.asyncio
async def test_trade_missing_collection_number_reports_usage() -> None:
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            create_trade_from_collection_number=AsyncMock(),
        ),
        trade_display_service=SimpleNamespace(
            get_trade_display=AsyncMock(),
        ),
    )
    cog = TradeCog(core)
    ctx = SimpleNamespace(send=AsyncMock())
    error = commands.MissingRequiredArgument.__new__(
        commands.MissingRequiredArgument,
    )
    error.param = inspect.Parameter(
        "collection_number",
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )

    await cog.trade_error(ctx, error)

    ctx.send.assert_awaited_once_with("Usage: !trade @trainer <collection number>")


@pytest.mark.asyncio
async def test_trade_reports_application_errors() -> None:
    create_trade = AsyncMock(
        side_effect=TradeCreatureNotOwned(101, 11),
    )
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            create_trade_from_collection_number=create_trade,
        ),
        trade_display_service=SimpleNamespace(
            get_trade_display=AsyncMock(),
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
            create_trade_from_collection_number=create_trade,
        ),
        trade_display_service=SimpleNamespace(
            get_trade_display=AsyncMock(),
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
