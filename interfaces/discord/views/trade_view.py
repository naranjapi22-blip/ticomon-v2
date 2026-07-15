from __future__ import annotations

from datetime import UTC, datetime

import discord

from application.bootstrap.core import CoreServices
from application.trade.exceptions import (
    TradeApplicationError,
    TradeNotFound,
)
from application.trade.trade_display import (
    TradeCreatureDisplay,
    TradeDisplay,
    TradeOfferDisplay,
)
from core.trade.exceptions import (
    InvalidTradeState,
    TradeNotParticipant,
)
from core.trade.trade_status import TradeStatus
from interfaces.discord.achievement_notifications import send_unlocks
from interfaces.discord.buttons.trade_accept_button import AcceptButton
from interfaces.discord.buttons.trade_cancel_button import CancelButton
from interfaces.discord.buttons.trade_edit_offer_button import EditOfferButton
from interfaces.discord.buttons.trade_reject_button import RejectButton
from interfaces.discord.views.trade_edit_offer_modal import TradeEditOfferModal


class TradeView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        trade_display: TradeDisplay,
    ) -> None:
        super().__init__(timeout=300)

        self.core = core
        self.trade_display = trade_display
        self.trade_id = trade_display.trade_id
        self.message: discord.Message | None = None

        self.build_components()

    def build_components(self) -> None:
        self.clear_items()

        self.add_item(
            AcceptButton(),
        )
        self.add_item(
            RejectButton(),
        )
        self.add_item(
            EditOfferButton(),
        )
        self.add_item(
            CancelButton(),
        )

        if self.trade_display.status in {
            TradeStatus.COMPLETED,
            TradeStatus.CANCELLED,
            TradeStatus.REJECTED,
            TradeStatus.EXPIRED,
        }:
            for child in self.children:
                child.disabled = True

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"⚖️ Trade #{self.trade_display.trade_id}",
            description="Current trade negotiation.\nUse the buttons below to respond.",
            color=self._color(),
        )

        embed.add_field(
            name="Initiator",
            value=f"<@{self.trade_display.initiator_trainer_id}>",
            inline=True,
        )
        embed.add_field(
            name="Counterparty",
            value=f"<@{self.trade_display.counterparty_trainer_id}>",
            inline=True,
        )
        embed.add_field(
            name="Status",
            value=self.trade_display.status.value.title(),
            inline=True,
        )

        embed.add_field(
            name="Initiator Offer",
            value=self._format_offer(self.trade_display.initiator_offer),
            inline=False,
        )
        embed.add_field(
            name="Counterparty Offer",
            value=self._format_offer(self.trade_display.counterparty_offer),
            inline=False,
        )

        if self.trade_display.completed_at is not None:
            embed.add_field(
                name="Completed At",
                value=self.trade_display.completed_at.isoformat(),
                inline=False,
            )

        return embed

    async def accept(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self._apply_trade_action(
            interaction,
            self.core.trade_application.accept_trade,
        )

    async def reject(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self._apply_trade_action(
            interaction,
            self.core.trade_application.reject_trade,
        )

    async def cancel(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self._apply_trade_action(
            interaction,
            self.core.trade_application.cancel_trade,
        )

    async def edit_offer(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.send_modal(
            TradeEditOfferModal(
                self.core,
                trade_id=self.trade_id,
                trainer_id=interaction.user.id,
                trade_view=self,
            )
        )

    async def refresh(self) -> None:
        await self._reload_trade_display()

        if self.message is not None:
            await self.message.edit(
                embed=self.build_embed(),
                view=self,
            )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id not in {
            self.trade_display.initiator_trainer_id,
            self.trade_display.counterparty_trainer_id,
        }:
            await interaction.response.send_message(
                "❌ Only the trade participants can use these controls.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(
                view=self,
            )

    async def _apply_trade_action(
        self,
        interaction: discord.Interaction,
        action,
    ) -> None:
        await interaction.response.defer()

        try:
            result = await action(
                trade_id=self.trade_id,
                trainer_id=interaction.user.id,
                at=datetime.now(UTC),
            )
        except (TradeNotFound, InvalidTradeState, TradeNotParticipant) as error:
            await interaction.followup.send(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        except TradeApplicationError as error:
            await interaction.followup.send(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        await send_unlocks(
            interaction.followup.send,
            getattr(result, "achievements_by_trainer", {}).get(interaction.user.id, ()),
            context="trade",
        )

        await self._reload_trade_display()
        await self._edit_message()

    async def _reload_trade_display(self) -> None:
        self.trade_display = await self.core.trade_display_service.get_trade_display(
            self.trade_id,
        )
        self.build_components()

    async def _edit_message(self) -> None:
        if self.message is not None:
            await self.message.edit(
                embed=self.build_embed(),
                view=self,
            )

    @staticmethod
    def _format_offer(
        offer: TradeOfferDisplay | None,
    ) -> str:
        if offer is None or offer.creature is None:
            offer_text = "No creature offered yet."
        else:
            offer_text = TradeView._format_creature(offer.creature)

        if offer is not None and offer.accepted_at is not None:
            offer_text += f"\n\nAcceptance: Accepted at {offer.accepted_at.isoformat()}"
        else:
            offer_text += "\n\nAcceptance: Pending"

        return offer_text

    @staticmethod
    def _format_creature(creature: TradeCreatureDisplay) -> str:
        lines = [
            f"**{creature.species_name}** • #{creature.collection_number}",
            (
                f"IVs: {creature.iv_percentage}% • "
                f"Shiny: {'Yes' if creature.is_shiny else 'No'}"
            ),
            f"Nature: {creature.nature} • Size: {creature.size}",
            f"Offered by: <@{creature.trainer_id}>",
        ]

        if creature.current_form_name is not None:
            lines.insert(3, f"Form: {creature.current_form_name}")

        return "\n".join(lines)

    def _color(self) -> discord.Color:
        if self.trade_display.status is TradeStatus.COMPLETED:
            return discord.Color.green()

        if self.trade_display.status in {
            TradeStatus.CANCELLED,
            TradeStatus.REJECTED,
            TradeStatus.EXPIRED,
        }:
            return discord.Color.red()

        return discord.Color.blurple()
