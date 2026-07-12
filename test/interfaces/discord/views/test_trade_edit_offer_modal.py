from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from application.trade.trade_display import (
    TradeCreatureDisplay,
    TradeDisplay,
    TradeOfferDisplay,
)
from core.trade.trade_status import TradeStatus
from interfaces.discord.views.trade_edit_offer_modal import TradeEditOfferModal
from interfaces.discord.views.trade_view import TradeView


def make_trade_display() -> TradeDisplay:
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
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOfferDisplay(
            trainer_id=101,
            creature=creature,
            accepted_at=None,
        ),
        counterparty_offer=TradeOfferDisplay(
            trainer_id=202,
            creature=TradeCreatureDisplay(
                creature_id=33,
                trainer_id=202,
                species_name="Eevee",
                collection_number=14,
                iv_percentage=100,
                is_shiny=False,
                nature="Hardy",
                size="M (1.00×)",
                current_form_name=None,
            ),
            accepted_at=None,
        ),
        status=TradeStatus.OPEN,
        completed_at=None,
        cancelled_by_trainer_id=None,
        rejected_by_trainer_id=None,
    )


@pytest.mark.asyncio
async def test_edit_offer_button_opens_modal() -> None:
    core = SimpleNamespace(
        trade_display_service=AsyncMock(),
    )
    trade = make_trade_display()
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
async def test_modal_submits_collection_number_to_application() -> None:
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            set_offer_from_collection_number=AsyncMock(),
        ),
    )
    trade_view = SimpleNamespace(refresh=AsyncMock())
    modal = TradeEditOfferModal(
        core,
        trade_id=42,
        trainer_id=101,
        trade_view=trade_view,
    )
    modal.collection_number._value = "7"
    interaction = SimpleNamespace(
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await modal.on_submit(interaction)

    core.trade_application.set_offer_from_collection_number.assert_awaited_once_with(
        trade_id=42,
        trainer_id=101,
        collection_number=7,
        at=ANY,
    )
    trade_view.refresh.assert_awaited_once()
    interaction.response.send_message.assert_awaited_once_with(
        "✅ Offer updated.",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_modal_rejects_invalid_collection_number() -> None:
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            set_offer_from_collection_number=AsyncMock(),
        ),
    )
    modal = TradeEditOfferModal(
        core,
        trade_id=42,
        trainer_id=101,
        trade_view=SimpleNamespace(refresh=AsyncMock()),
    )
    modal.collection_number._value = "abc"
    interaction = SimpleNamespace(
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await modal.on_submit(interaction)

    interaction.response.send_message.assert_awaited_once_with(
        "❌ Collection number must be an integer.",
        ephemeral=True,
    )
