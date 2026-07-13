from discord.ext import commands

from application.bootstrap.core import CoreServices
from interfaces.discord.cogs.collection_display import (
    build_empty_message,
    build_top_title,
    format_creature_entry,
)
from interfaces.discord.views.creature_list_view import CreatureListView


class TopCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(name="top")
    async def top(
        self,
        ctx: commands.Context,
        pokemon_type: str | None = None,
    ):
        try:
            creatures = await self.core.creature_collection_service.get_top_collection(
                trainer_id=ctx.author.id,
                pokemon_type=pokemon_type,
            )
        except ValueError as error:
            await ctx.send(str(error))
            return

        normalized_type = pokemon_type.strip() if pokemon_type is not None else None

        if not creatures:
            await ctx.send(
                build_empty_message(
                    type_name=normalized_type,
                    shiny_only=False,
                )
            )
            return

        view = CreatureListView(
            author_id=ctx.author.id,
            title=build_top_title(normalized_type),
            entries=[format_creature_entry(creature) for creature in creatures],
        )

        message = await ctx.send(
            embed=view.build_embed(),
            view=view,
        )

        view.message = message
