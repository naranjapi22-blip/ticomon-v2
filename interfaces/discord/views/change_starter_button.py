import discord


class ChangeStarterButton(discord.ui.Button):

    def __init__(
        self,
    ):
        super().__init__(
            label="Change Starter",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await self.view.change_starter(
            interaction,
        )
