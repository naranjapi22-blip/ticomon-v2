import discord


class RejectButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Reject",
            style=discord.ButtonStyle.danger,
            emoji="❌",
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.view.reject(
            interaction,
        )
