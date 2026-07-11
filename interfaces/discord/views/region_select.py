import discord

from core.starter.starter_catalog import STARTER_REGIONS


class RegionSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(
                label=region,
                value=region,
            )
            for region in STARTER_REGIONS.keys()
        ]

        super().__init__(
            placeholder="Choose your region...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        await self.view.choose_region(
            interaction,
            self.values[0],
        )
