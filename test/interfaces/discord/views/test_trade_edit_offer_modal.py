from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from core.trade.trade import Trade
from core.trade.trade_offer import TradeOffer
from core.trade.trade_status import TradeStatus
from interfaces.discord.views.trade_edit_offer_modal import TradeEditOfferModal
from interfaces.discord.views.trade_view import TradeView


def make_trade(*, counterparty_creatures: list[int] | None = None) -> Trade:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return Trade._reconstitute(
        trade_id=42,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOffer.create(101, 11),
        counterparty_offer=TradeOffer.create(202, (counterparty_creatures or [33])[0]),
        created_at=created_at,
        expires_at=None,
        status=TradeStatus.OPEN,
        initiator_accepted_at=None,
        counterparty_accepted_at=None,
        completed_at=None,
    )


@pytest.mark.asyncio
async def test_edit_offer_button_opens_modal() -> None:
    core = SimpleNamespace()
    trade = make_trade()
    view = TradeView(core, trade)
    send_modal = AsyncMock()
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=101),
        response=SimpleNamespace(send_modal=send_modal, send_message=AsyncMock()),
    )

    await view.children[2].callback(interaction)

    send_modal.assert_awaited_once()
    modal = send_modal.await_args.args[0]
    assert isinstance(modal, TradeEditOfferModal)


@pytest.mark.asyncio
async def test_modal_submits_collection_numbers_to_application() -> None:
    updated_trade = Trade._reconstitute(
        trade_id=42,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOffer.create(101, 11),
        counterparty_offer=TradeOffer.create(202, 44),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        expires_at=None,
        status=TradeStatus.OPEN,
        initiator_accepted_at=None,
        counterparty_accepted_at=None,
        completed_at=None,
    )
    set_offer = AsyncMock(return_value=updated_trade)
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            set_offer_from_collection_numbers=set_offer,
        ),
    )
    trade_view = TradeView(
        core,
        make_trade(),
    )
    trade_view.message = AsyncMock()
    modal = TradeEditOfferModal(
        core,
        trade_id=42,
        trainer_id=101,
        trade_view=trade_view,
    )
    modal.collection_numbers._value = "7, 14"
    interaction = SimpleNamespace(
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await modal.on_submit(interaction)

    set_offer.assert_awaited_once_with(
        trade_id=42,
        trainer_id=101,
        collection_numbers=[7, 14],
        at=ANY,
    )
    interaction.response.send_message.assert_awaited_once_with(
        "✅ Offer updated.",
        ephemeral=True,
    )
    trade_view.message.edit.assert_awaited_once()
    embed = trade_view.message.edit.await_args.kwargs["embed"]
    assert "Creature #44" in embed.fields[4].value
    assert "Acceptance: Pending" in embed.fields[3].value
    assert "Acceptance: Pending" in embed.fields[4].value


@pytest.mark.asyncio
async def test_modal_rejects_invalid_collection_numbers() -> None:
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            set_offer_from_collection_numbers=AsyncMock(),
        ),
    )
    modal = TradeEditOfferModal(
        core,
        trade_id=42,
        trainer_id=101,
        trade_view=TradeView(core, make_trade()),
    )
    modal.collection_numbers._value = "abc"
    interaction = SimpleNamespace(
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await modal.on_submit(interaction)

    interaction.response.send_message.assert_awaited_once_with(
        "❌ Collection numbers must be a comma-separated list of integers.",
        ephemeral=True,
    )
