from __future__ import annotations

import re
from datetime import UTC, datetime

import discord

from application.trade.exceptions import TradeApplicationError
from core.trade.exceptions import TradeError


class TradeEditOfferModal(discord.ui.Modal, title="Edit Trade Offer"):
    def __init__(
        self,
        core,
        trade_id: int,
        trainer_id: int,
        trade_view,
    ) -> None:
        super().__init__()

        self._core = core
        self._trade_id = trade_id
        self._trainer_id = trainer_id
        self._trade_view = trade_view

        self.collection_number = discord.ui.TextInput(
            label="Collection number",
            placeholder="12",
            required=True,
            max_length=32,
        )
        self.add_item(self.collection_number)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            collection_number = self._parse_collection_number(
                self.collection_number.value,
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Collection number must be an integer.",
                ephemeral=True,
            )
            return

        try:
            await self._core.trade_application.set_offer_from_collection_number(
                trade_id=self._trade_id,
                trainer_id=self._trainer_id,
                collection_number=collection_number,
                at=datetime.now(UTC),
            )
        except (TradeApplicationError, TradeError) as error:
            await interaction.response.send_message(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        await self._trade_view.refresh()

        await interaction.response.send_message(
            "✅ Offer updated.",
            ephemeral=True,
        )

    @staticmethod
    def _parse_collection_number(value: str) -> int:
        normalized = value.strip()

        if not normalized:
            raise ValueError("No collection number was provided.")

        if re.search(r"[,\s]", normalized):
            raise ValueError("Collection number must be singular.")

        return int(normalized)
