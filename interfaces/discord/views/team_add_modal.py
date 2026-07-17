from __future__ import annotations

import discord

from application.bootstrap.core import CoreServices
from application.team.exceptions import TeamApplicationError
from interfaces.discord.input_normalizer import parse_collection_number


class TeamAddModal(discord.ui.Modal, title="Add to Team"):
    def __init__(
        self,
        core: CoreServices,
        trainer_id: int,
        team_view,
    ) -> None:
        super().__init__()

        self._core = core
        self._trainer_id = trainer_id
        self._team_view = team_view

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
            collection_number = parse_collection_number(
                self.collection_number.value,
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Collection number must be an integer.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        try:
            await self._core.team_application_service.add_to_team(
                trainer_id=self._trainer_id,
                collection_number=collection_number,
            )
        except TeamApplicationError as error:
            await interaction.followup.send(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        await self._team_view.refresh()
        await interaction.followup.send(
            f"✅ Creature #{collection_number} was added to your team.",
            ephemeral=True,
        )
