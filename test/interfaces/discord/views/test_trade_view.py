from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from application.trade.trade_display import (
    TradeCreatureDisplay,
    TradeDisplay,
    TradeOfferDisplay,
)
from core.trade.trade_status import TradeStatus
from interfaces.discord.buttons.trade_accept_button import AcceptButton
from interfaces.discord.buttons.trade_cancel_button import CancelButton
from interfaces.discord.buttons.trade_edit_offer_button import EditOfferButton
from interfaces.discord.buttons.trade_reject_button import RejectButton
from interfaces.discord.views.trade_view import TradeView


def _creature(
    *,
    creature_id: int,
    trainer_id: int,
    species_name: str,
    collection_number: int,
    current_form_name: str | None = None,
) -> TradeCreatureDisplay:
    return TradeCreatureDisplay(
        creature_id=creature_id,
        trainer_id=trainer_id,
        species_name=species_name,
        collection_number=collection_number,
        iv_percentage=97,
        is_shiny=creature_id % 2 == 0,
        nature="Jolly",
        size="L (1.12×)",
        current_form_name=current_form_name,
    )


def make_trade_display(*, status: TradeStatus = TradeStatus.OPEN) -> TradeDisplay:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    return TradeDisplay(
        trade_id=42,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOfferDisplay(
            trainer_id=101,
            creature=_creature(
                creature_id=11,
                trainer_id=101,
                species_name="Pikachu",
                collection_number=7,
                current_form_name="Rockstar",
            ),
            accepted_at=created_at,
        ),
        counterparty_offer=TradeOfferDisplay(
            trainer_id=202,
            creature=_creature(
                creature_id=33,
                trainer_id=202,
                species_name="Eevee",
                collection_number=14,
            ),
            accepted_at=None,
        ),
        status=status,
        completed_at=created_at if status is TradeStatus.COMPLETED else None,
        cancelled_by_trainer_id=None,
        rejected_by_trainer_id=None,
    )


@pytest.mark.asyncio
async def test_trade_view_renders_current_offers() -> None:
    view = TradeView(
        SimpleNamespace(
            trade_display_service=AsyncMock(),
        ),
        make_trade_display(),
    )

    embed = view.build_embed()

    assert embed.title == "⚖️ Trade #42"
    assert embed.fields[3].name == "Initiator Offer"
    assert "Pikachu" in embed.fields[3].value
    assert "#7" in embed.fields[3].value
    assert "IVs: 97%" in embed.fields[3].value
    assert "Shiny: No" in embed.fields[3].value
    assert "Nature: Jolly" in embed.fields[3].value
    assert "Size: L (1.12×)" in embed.fields[3].value
    assert "Form: Rockstar" in embed.fields[3].value
    assert "Offered by: <@101>" in embed.fields[3].value
    assert "Acceptance: Accepted at" in embed.fields[3].value
    assert embed.fields[4].name == "Counterparty Offer"
    assert "Eevee" in embed.fields[4].value
    assert "Offered by: <@202>" in embed.fields[4].value
    assert "Acceptance: Pending" in embed.fields[4].value
    assert isinstance(view.children[0], AcceptButton)
    assert isinstance(view.children[1], RejectButton)
    assert isinstance(view.children[2], EditOfferButton)
    assert isinstance(view.children[3], CancelButton)
    assert view.children[0].row == 0
    assert view.children[1].row == 0
    assert view.children[2].row == 1
    assert view.children[3].row == 1


@pytest.mark.asyncio
async def test_trade_view_refresh_edits_message() -> None:
    updated_display = TradeDisplay(
        trade_id=42,
        initiator_trainer_id=101,
        counterparty_trainer_id=202,
        initiator_offer=TradeOfferDisplay(
            trainer_id=101,
            creature=_creature(
                creature_id=11,
                trainer_id=101,
                species_name="Pikachu",
                collection_number=7,
                current_form_name="Rockstar",
            ),
            accepted_at=None,
        ),
        counterparty_offer=TradeOfferDisplay(
            trainer_id=202,
            creature=_creature(
                creature_id=44,
                trainer_id=202,
                species_name="Umbreon",
                collection_number=15,
            ),
            accepted_at=None,
        ),
        status=TradeStatus.OPEN,
        completed_at=None,
        cancelled_by_trainer_id=None,
        rejected_by_trainer_id=None,
    )
    trade_display_service = AsyncMock(
        get_trade_display=AsyncMock(return_value=updated_display),
    )
    view = TradeView(
        SimpleNamespace(
            trade_display_service=trade_display_service,
        ),
        make_trade_display(),
    )
    view.message = AsyncMock()

    await view.refresh()

    trade_display_service.get_trade_display.assert_awaited_once_with(42)
    view.message.edit.assert_awaited_once()
    embed = view.message.edit.await_args.kwargs["embed"]
    assert "Umbreon" in embed.fields[4].value
    assert "Acceptance: Pending" in embed.fields[3].value
    assert "Acceptance: Pending" in embed.fields[4].value


@pytest.mark.asyncio
async def test_accept_button_calls_application_service() -> None:
    trade_display = make_trade_display()
    updated_display = make_trade_display()
    accept_trade = AsyncMock(return_value=SimpleNamespace())
    trade_display_service = AsyncMock(
        get_trade_display=AsyncMock(return_value=updated_display),
    )
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            accept_trade=accept_trade,
            reject_trade=AsyncMock(),
            cancel_trade=AsyncMock(),
        ),
        trade_display_service=trade_display_service,
    )
    view = TradeView(
        core,
        trade_display,
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
    trade_display_service.get_trade_display.assert_awaited_once_with(42)
    interaction.response.edit_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_button_calls_application_service() -> None:
    trade_display = make_trade_display()
    trade_display_service = AsyncMock(
        get_trade_display=AsyncMock(
            return_value=make_trade_display(status=TradeStatus.REJECTED)
        ),
    )
    reject_trade = AsyncMock(return_value=SimpleNamespace())
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            accept_trade=AsyncMock(),
            reject_trade=reject_trade,
            cancel_trade=AsyncMock(),
        ),
        trade_display_service=trade_display_service,
    )
    view = TradeView(
        core,
        trade_display,
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
    trade_display = make_trade_display()
    trade_display_service = AsyncMock(
        get_trade_display=AsyncMock(
            return_value=make_trade_display(status=TradeStatus.CANCELLED)
        ),
    )
    cancel_trade = AsyncMock(return_value=SimpleNamespace())
    core = SimpleNamespace(
        trade_application=SimpleNamespace(
            accept_trade=AsyncMock(),
            reject_trade=AsyncMock(),
            cancel_trade=cancel_trade,
        ),
        trade_display_service=trade_display_service,
    )
    view = TradeView(
        core,
        trade_display,
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
        SimpleNamespace(
            trade_display_service=AsyncMock(),
        ),
        make_trade_display(status=TradeStatus.CANCELLED),
    )

    assert all(child.disabled for child in view.children)


@pytest.mark.asyncio
async def test_timeout_disables_and_edits_message() -> None:
    view = TradeView(
        SimpleNamespace(
            trade_display_service=AsyncMock(),
        ),
        make_trade_display(),
    )
    view.message = AsyncMock()

    await view.on_timeout()

    assert all(child.disabled for child in view.children)
    view.message.edit.assert_awaited_once_with(view=view)
