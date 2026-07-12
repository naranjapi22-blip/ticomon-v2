import discord


class AcceptButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Accept",
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.view.accept(
            interaction,
        )
