from __future__ import annotations

import discord

from application.bootstrap.core import CoreServices
from interfaces.discord.views.team_view import TeamView


class TeamLauncherView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        trainer_id: int,
    ) -> None:
        super().__init__(timeout=120)

        self.core = core
        self.trainer_id = trainer_id
        self.message: discord.Message | None = None

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "❌ This is not your team command.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    @discord.ui.button(
        label="Open Team",
        style=discord.ButtonStyle.primary,
        emoji="📋",
    )
    async def open_team(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.defer(
            ephemeral=True,
            thinking=True,
        )

        team_view = await TeamView.create(
            self.core,
            self.trainer_id,
        )

        team_view.message = await interaction.followup.send(
            embed=team_view.build_embed(),
            view=team_view,
            ephemeral=True,
            wait=True,
        )

        if self.message is not None:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass

        self.stop()
