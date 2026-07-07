import discord

from interfaces.discord.views.capture_view import CaptureView


class OpportunityButton(discord.ui.Button):
    def __init__(
        self,
        core,
        index: int,
        label: str,
    ):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
        )

        self._core = core
        self._index = index

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await self._core.select_opportunity_application.select_opportunity(
            opportunity_index=self._index,
        )

        await interaction.response.edit_message(
            content=f"Selected option {self._index}.",
            view=CaptureView(self._core),
        )
