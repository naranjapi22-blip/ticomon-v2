from datetime import UTC, datetime

import discord

from application.bootstrap.core import CoreServices
from application.trade.exceptions import (
    TradeApplicationError,
    TradeNotFound,
)
from core.trade.exceptions import (
    InvalidTradeState,
    TradeNotParticipant,
)
from core.trade.trade import Trade
from core.trade.trade_status import TradeStatus
from interfaces.discord.buttons.trade_accept_button import AcceptButton
from interfaces.discord.buttons.trade_cancel_button import CancelButton
from interfaces.discord.buttons.trade_edit_offer_button import EditOfferButton
from interfaces.discord.buttons.trade_reject_button import RejectButton
from interfaces.discord.views.trade_edit_offer_modal import TradeEditOfferModal


class TradeView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        trade: Trade,
    ) -> None:
        super().__init__(timeout=300)

        self.core = core
        self.trade = trade
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

        if self.trade.is_terminal:
            for child in self.children:
                child.disabled = True

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"⚖️ Trade #{self.trade.id}",
            description=(
                "Current trade negotiation.\n" "Use the buttons below to respond."
            ),
            color=self._color(),
        )

        embed.add_field(
            name="Initiator",
            value=f"<@{self.trade.initiator_trainer_id}>",
            inline=True,
        )
        embed.add_field(
            name="Counterparty",
            value=f"<@{self.trade.counterparty_trainer_id}>",
            inline=True,
        )
        embed.add_field(
            name="Status",
            value=self.trade.status.value.title(),
            inline=True,
        )

        embed.add_field(
            name="Initiator Offer",
            value=self._format_offer(
                self.trade.initiator_offer.creature_ids,
                accepted_at=self.trade.initiator_accepted_at,
            ),
            inline=False,
        )
        embed.add_field(
            name="Counterparty Offer",
            value=self._format_offer(
                (
                    self.trade.counterparty_offer.creature_ids
                    if self.trade.counterparty_offer is not None
                    else None
                ),
                accepted_at=self.trade.counterparty_accepted_at,
            ),
            inline=False,
        )

        if self.trade.completed_at is not None:
            embed.add_field(
                name="Completed At",
                value=self.trade.completed_at.isoformat(),
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
                trade_id=self.trade.id,
                trainer_id=interaction.user.id,
            )
        )

    async def refresh(
        self,
        interaction: discord.Interaction,
        trade: Trade | None = None,
    ) -> None:
        if trade is not None:
            self.trade = trade
        else:
            self.trade = await self.core.trade_application.get_trade(
                self.trade.id,
            )

        self.build_components()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id not in {
            self.trade.initiator_trainer_id,
            self.trade.counterparty_trainer_id,
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
        try:
            trade = await action(
                trade_id=self.trade.id,
                trainer_id=interaction.user.id,
                at=datetime.now(UTC),
            )
        except (TradeNotFound, InvalidTradeState, TradeNotParticipant) as error:
            await interaction.response.send_message(
                f"❌ {error}",
                ephemeral=True,
            )
            return
        except TradeApplicationError as error:
            await interaction.response.send_message(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        self.trade = trade
        self.build_components()

        if trade.status is TradeStatus.COMPLETED:
            await interaction.response.edit_message(
                content="✅ Trade completed.",
                embed=self.build_embed(),
                view=self,
            )
            return

        if trade.status is TradeStatus.CANCELLED:
            await interaction.response.edit_message(
                content="❌ Trade cancelled.",
                embed=self.build_embed(),
                view=self,
            )
            return

        if trade.status is TradeStatus.REJECTED:
            await interaction.response.edit_message(
                content="❌ Trade rejected.",
                embed=self.build_embed(),
                view=self,
            )
            return

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    @staticmethod
    def _format_offer(
        creature_ids: tuple[int, ...] | None,
        *,
        accepted_at: datetime | None,
    ) -> str:
        if not creature_ids:
            offer_text = "No creatures offered yet."
        else:
            offer_text = "\n".join(
                f"• Creature #{creature_id}" for creature_id in creature_ids
            )

        if accepted_at is not None:
            offer_text += f"\n\nAccepted at {accepted_at.isoformat()}"

        return offer_text

    def _color(self) -> discord.Color:
        if self.trade.status is TradeStatus.COMPLETED:
            return discord.Color.green()

        if self.trade.status in {
            TradeStatus.CANCELLED,
            TradeStatus.REJECTED,
            TradeStatus.EXPIRED,
        }:
            return discord.Color.red()

        return discord.Color.blurple()
