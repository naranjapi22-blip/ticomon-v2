import discord

from interfaces.discord.images import get_opportunity_gif
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
                "This !spawn has already ended.",
                ephemeral=True,
            )
            return

        if interaction.user.id != session.owner_id:
            await interaction.response.send_message(
                "Only the trainer who started the !spawn can select a Pokémon.",
                ephemeral=True,
            )
            return

        await self._core.select_opportunity_application.select_opportunity(
            guild_id=interaction.guild.id,
            opportunity_index=self._index,
        )

        selected = session.selected_opportunity

        gif_url = get_opportunity_gif(selected)

        embed = discord.Embed(
            title=(
                f"{selected.species.name.title()} "
                f"{selected.initial_form.name.title()}"
                if selected.initial_form
                else selected.species.name.title()
            ),
            description=f"**{selected.species.spawn_rarity.name.replace('_', ' ')}**",
        )

        embed.set_image(
            url=gif_url,
        )

        view = CaptureView(self._core)

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            attachments=[],
            view=view,
        )

        view.message = await interaction.original_response()
