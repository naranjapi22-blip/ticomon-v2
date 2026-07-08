import discord

from interfaces.discord.images import get_species_gif
from interfaces.discord.views.capture_view import CaptureView


class OpportunityButton(discord.ui.Button):
    def __init__(
        self,
        core,
        index: int,
        label: str,
    ):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
        )

        self._core = core
        self._index = index

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
        session = await self._core.get_current_spawn_application.get_current(
            guild_id=interaction.guild.id,
        )

        if session is None:
            await interaction.response.send_message(
                "Este !spawn ya terminó.",
                ephemeral=True,
            )
            return

        if interaction.user.id != session.owner_id:
            await interaction.response.send_message(
                "Solo quien inició el !spawn puede elegir un Pokémon.",
                ephemeral=True,
            )
            return

        await self._core.select_opportunity_application.select_opportunity(
            guild_id=interaction.guild.id,
            opportunity_index=self._index,
        )

        selected = session.selected_opportunity

        gif_url = get_species_gif(
            species_id=selected.species.id,
            shiny=selected.is_shiny,
        )

        embed = discord.Embed(
            title=selected.species.name.title(),
            description=f"**{selected.species.spawn_rarity.name.replace('_', ' ')}**",
        )

        embed.set_image(
            url=gif_url,
        )

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=CaptureView(
                self._core,
            ),
        )
