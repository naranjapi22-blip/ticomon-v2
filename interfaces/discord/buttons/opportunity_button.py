import logging

import discord

from interfaces.discord.images import (
    download_gif_file,
    get_opportunity_gif,
    get_species_gif,
)
from interfaces.discord.views.capture_view import CaptureView

logger = logging.getLogger(__name__)
_MISSING_SPAWN_RESOURCES: set[tuple[int, int | None]] = set()


async def _opportunity_gif_file(opportunity):
    gif_url = get_opportunity_gif(opportunity)

    try:
        return await download_gif_file(gif_url, "spawn.gif")
    except Exception:
        variant_id = (
            opportunity.initial_form.id
            if opportunity.initial_form is not None
            else None
        )
        key = (opportunity.species.id, variant_id)

        if key not in _MISSING_SPAWN_RESOURCES:
            _MISSING_SPAWN_RESOURCES.add(key)
            logger.warning(
                "spawn_gif_resource_missing species_id=%s variant_id=%s "
                "canonical_name=%s asset_key=%s",
                opportunity.species.id,
                variant_id,
                (
                    f"{opportunity.species.name}:{opportunity.initial_form.name}"
                    if opportunity.initial_form is not None
                    else opportunity.species.name
                ),
                gif_url,
            )

        try:
            return await download_gif_file(
                get_species_gif(
                    opportunity.species.pokeapi_id,
                    opportunity.is_shiny,
                ),
                "spawn.gif",
            )
        except Exception:
            return None


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

        await interaction.response.defer()

        await self._core.select_opportunity_application.select_opportunity(
            guild_id=interaction.guild.id,
            opportunity_index=self._index,
        )

        selected = session.selected_opportunity

        gif_file = await _opportunity_gif_file(selected)

        embed = discord.Embed(
            title=(
                f"{selected.species.name.title()} "
                f"{selected.initial_form.name.title()}"
                if selected.initial_form
                else selected.species.name.title()
            ),
            description=f"**{selected.species.spawn_rarity.name.replace('_', ' ')}**",
        )

        if gif_file is not None:
            embed.set_image(url="attachment://spawn.gif")

        view = CaptureView(self._core)

        await interaction.edit_original_response(
            content=None,
            embed=embed,
            attachments=[gif_file] if gif_file is not None else [],
            view=view,
        )

        view.message = await interaction.original_response()
