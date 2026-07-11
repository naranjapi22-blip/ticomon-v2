import discord

from core.species.species import Species


class StarterSelect(discord.ui.Select):

    def __init__(
        self,
        starters: list[Species],
    ):
        options = [
            discord.SelectOption(
                label=starter.name,
                value=str(starter.id),
            )
            for starter in starters
        ]

        super().__init__(
            placeholder="Choose your starter...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        view = self.view

        species_id = int(
            self.values[0],
        )

        await view.choose_starter(
            interaction,
            species_id,
        )
