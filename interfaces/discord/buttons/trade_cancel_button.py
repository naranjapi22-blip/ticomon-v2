import discord


class CancelButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Cancel",
            style=discord.ButtonStyle.secondary,
            emoji="✖️",
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.view.cancel(
            interaction,
        )
