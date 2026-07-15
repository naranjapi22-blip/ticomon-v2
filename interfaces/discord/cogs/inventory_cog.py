from discord.ext import commands

from application.bootstrap.core import CoreServices
from interfaces.discord.cogs.collection_display import (
    build_empty_message,
    build_recent_title,
    format_creature_entry,
)
from interfaces.discord.input_normalizer import normalize_text
from interfaces.discord.views.creature_list_view import CreatureListView


class InventoryCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(name="inventory")
    async def inventory(
        self,
        ctx: commands.Context,
        filter_value: str | None = None,
    ):
        normalized_filter = (
            normalize_text(filter_value) if filter_value is not None else None
        )
        shiny_only = normalized_filter == "shiny"
        pokemon_type = None if shiny_only else normalized_filter

        try:
            creatures = (
                await self.core.creature_collection_service.get_recent_collection(
                    trainer_id=ctx.author.id,
                    pokemon_type=pokemon_type,
                    shiny_only=shiny_only,
                )
            )
        except ValueError as error:
            await ctx.send(str(error))
            return

        normalized_type = pokemon_type

        if not creatures:
            await ctx.send(
                build_empty_message(
                    type_name=normalized_type,
                    shiny_only=shiny_only,
                )
            )
            return

        view = CreatureListView(
            author_id=ctx.author.id,
            title=build_recent_title(
                normalized_type,
                shiny_only,
            ),
            entries=[format_creature_entry(creature) for creature in creatures],
        )

        message = await ctx.send(
            embed=view.build_embed(),
            view=view,
        )

        view.message = message
