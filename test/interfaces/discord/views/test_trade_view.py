from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from core.trade.trade import Trade
from core.trade.trade_offer import TradeOffer
from core.trade.trade_status import TradeStatus
from interfaces.discord.buttons.trade_accept_button import AcceptButton
from interfaces.discord.buttons.trade_cancel_button import CancelButton
from interfaces.discord.buttons.trade_edit_offer_button import EditOfferButton
from interfaces.discord.buttons.trade_reject_button import RejectButton
from interfaces.discord.views.trade_view import TradeView


def make_trade(*, status: TradeStatus = TradeStatus.OPEN) -> Trade:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return Trade._reconstitute(
        trade_id=42,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOffer.create(101, [11, 22]),
        counterparty_offer=TradeOffer.create(202, [33]),
        created_at=created_at,
        expires_at=None,
        status=status,
        initiator_accepted_at=None,
        counterparty_accepted_at=None,
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_trade_view_renders_current_offers() -> None:
    view = TradeView(
        SimpleNamespace(),
        make_trade(),
    )

    embed = view.build_embed()

    assert embed.title == "⚖️ Trade #42"
    assert embed.fields[3].name == "Initiator Offer"
    assert "Creature #11" in embed.fields[3].value
    assert embed.fields[4].name == "Counterparty Offer"
    assert "Creature #33" in embed.fields[4].value
    assert isinstance(view.children[0], AcceptButton)
    assert isinstance(view.children[1], RejectButton)
    assert isinstance(view.children[2], EditOfferButton)
    assert isinstance(view.children[3], CancelButton)
    assert view.children[0].row == 0
    assert view.children[1].row == 0
    assert view.children[2].row == 1
    assert view.children[3].row == 1


@pytest.mark.asyncio
async def test_accept_button_calls_application_service() -> None:
    trade = make_trade()
    updated_trade = make_trade(status=TradeStatus.OPEN)
    accept_trade = AsyncMock(return_value=updated_trade)
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            accept_trade=accept_trade,
            reject_trade=AsyncMock(),
            cancel_trade=AsyncMock(),
            get_trade=AsyncMock(),
        ),
    )
    view = TradeView(
        core,
        trade,
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=101),
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock()),
    )

    await view.children[0].callback(interaction)

    accept_trade.assert_awaited_once_with(
        trade_id=42,
        trainer_id=101,
        at=ANY,
    )
    interaction.response.edit_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_button_calls_application_service() -> None:
    trade = make_trade()
    updated_trade = make_trade(status=TradeStatus.REJECTED)
    reject_trade = AsyncMock(return_value=updated_trade)
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            accept_trade=AsyncMock(),
            reject_trade=reject_trade,
            cancel_trade=AsyncMock(),
            get_trade=AsyncMock(),
        ),
    )
    view = TradeView(
        core,
        trade,
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=202),
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock()),
    )

    await view.children[1].callback(interaction)

    reject_trade.assert_awaited_once_with(
        trade_id=42,
        trainer_id=202,
        at=ANY,
    )
    interaction.response.edit_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_button_calls_application_service() -> None:
    trade = make_trade()
    updated_trade = make_trade(status=TradeStatus.CANCELLED)
    cancel_trade = AsyncMock(return_value=updated_trade)
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            accept_trade=AsyncMock(),
            reject_trade=AsyncMock(),
            cancel_trade=cancel_trade,
            get_trade=AsyncMock(),
        ),
    )
    view = TradeView(
        core,
        trade,
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=101),
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock()),
    )

    await view.children[3].callback(interaction)

    cancel_trade.assert_awaited_once_with(
        trade_id=42,
        trainer_id=101,
        at=ANY,
    )
    interaction.response.edit_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_terminal_trade_disables_all_buttons() -> None:
    view = TradeView(
        SimpleNamespace(),
        make_trade(status=TradeStatus.CANCELLED),
    )

    assert all(child.disabled for child in view.children)
