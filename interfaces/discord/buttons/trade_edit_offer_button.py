import discord


class EditOfferButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Edit Offer",
            style=discord.ButtonStyle.primary,
            emoji="✏️",
            row=1,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await self.view.edit_offer(
            interaction,
        )
