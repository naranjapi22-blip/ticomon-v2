from __future__ import annotations

import discord

from application.bootstrap.core import CoreServices
from application.team.exceptions import TeamApplicationError
from interfaces.discord.input_normalizer import parse_collection_number


class TeamReplaceModal(discord.ui.Modal, title="Replace Team Member"):
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

        self.collection_number_to_replace = discord.ui.TextInput(
            label="Collection number to replace",
            placeholder="7",
            required=True,
            max_length=32,
        )
        self.new_collection_number = discord.ui.TextInput(
            label="New collection number",
            placeholder="14",
            required=True,
            max_length=32,
        )
        self.add_item(self.collection_number_to_replace)
        self.add_item(self.new_collection_number)

    async def on_submit(
        self,
        interaction: discord.Interaction,
    ) -> None:
        try:
            collection_number_to_replace = parse_collection_number(
                self.collection_number_to_replace.value,
            )
            new_collection_number = parse_collection_number(
                self.new_collection_number.value,
            )
        except ValueError:
            await interaction.response.send_message(
                "❌ Collection numbers must be integers.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        try:
            await self._core.team_application_service.replace_in_team(
                trainer_id=self._trainer_id,
                collection_number_to_replace=collection_number_to_replace,
                new_collection_number=new_collection_number,
            )
        except TeamApplicationError as error:
            await interaction.followup.send(
                f"❌ {error}",
                ephemeral=True,
            )
            return

        await self._team_view.refresh()
        await interaction.followup.send(
            (
                f"✅ Replaced #{collection_number_to_replace} with "
                f"#{new_collection_number}."
            ),
            ephemeral=True,
        )
