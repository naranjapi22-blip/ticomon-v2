import discord


class ConfirmButton(discord.ui.Button):

    def __init__(self):
        super().__init__(
            label="Begin Adventure",
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await self.view.confirm_starter(
            interaction,
        )
