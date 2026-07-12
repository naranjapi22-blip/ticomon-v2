from __future__ import annotations

import re
from datetime import UTC, datetime

import discord

from application.trade.exceptions import (
    TradeApplicationError,
)
from core.trade.exceptions import TradeError


class TradeEditOfferModal(discord.ui.Modal, title="Edit Trade Offer"):
    def __init__(
        self,
        core,
        trade_id: int,
        trainer_id: int,
    ) -> None:
        super().__init__()

        self._core = core
        self._trade_id = trade_id
        self._trainer_id = trainer_id

        self.collection_numbers = discord.ui.TextInput(
            label="Collection numbers",
            placeholder="12, 34, 57",
            required=True,
            max_length=500,
        )
        self.add_item(self.collection_numbers)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            collection_numbers = self._parse_collection_numbers(
                self.collection_numbers.value,
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Collection numbers must be a comma-separated list of integers.",
                ephemeral=True,
            )
            return

        try:
            await self._core.trade_application.set_offer_from_collection_numbers(
                trade_id=self._trade_id,
                trainer_id=self._trainer_id,
                collection_numbers=collection_numbers,
                at=datetime.now(UTC),
            )
        except (TradeApplicationError, TradeError) as error:
            await interaction.response.send_message(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "✅ Offer updated.",
            ephemeral=True,
        )

    @staticmethod
    def _parse_collection_numbers(value: str) -> list[int]:
        parts = [token for token in re.split(r"[,\s]+", value.strip()) if token]

        if not parts:
            raise ValueError("No collection numbers were provided.")

        return [int(part) for part in parts]
