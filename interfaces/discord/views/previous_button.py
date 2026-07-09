import discord


class PreviousButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            emoji="◀️",
            style=discord.ButtonStyle.secondary,
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.view

        if view.page == 0:
            return

        view.page -= 1

        await view.refresh(interaction)
