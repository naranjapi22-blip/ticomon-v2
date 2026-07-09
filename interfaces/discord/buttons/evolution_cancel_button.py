import discord


class EvolutionCancelButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="❌ Cancel",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):

        await interaction.response.edit_message(
            content="❌ Evolution cancelled.",
            view=None,
        )
