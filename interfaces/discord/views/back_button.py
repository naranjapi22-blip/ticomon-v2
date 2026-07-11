import discord


class BackButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await self.view.go_back(
            interaction,
        )
