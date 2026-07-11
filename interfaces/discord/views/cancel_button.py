import discord


class CancelButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Cancel",
            style=discord.ButtonStyle.danger,
            emoji="✖️",
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await self.view.cancel(
            interaction,
        )
