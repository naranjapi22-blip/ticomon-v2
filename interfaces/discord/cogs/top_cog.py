from discord.ext import commands

from application.bootstrap.core import CoreServices
from application.creature.creature_collection_service import TopMetric
from interfaces.discord.cogs.collection_display import (
    build_empty_message,
    build_top_title,
    format_creature_entry,
)
from interfaces.discord.input_normalizer import normalize_text
from interfaces.discord.views.creature_list_view import CreatureListView
from interfaces.discord.views.top_creature_view import TopCreatureView


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
        normalized_type = (
            normalize_text(pokemon_type) if pokemon_type is not None else None
        )

        try:
            rankings_service = getattr(
                self.core.creature_collection_service,
                "get_top_rankings",
                None,
            )
            if rankings_service is None:
                creatures = (
                    await self.core.creature_collection_service.get_top_collection(
                        trainer_id=ctx.author.id,
                        pokemon_type=normalized_type,
                    )
                )
            else:
                all_rankings = await rankings_service(
                    trainer_id=ctx.author.id,
                    metric=TopMetric.OVERALL,
                    pokemon_type=None,
                )
                rank_snapshot = getattr(
                    self.core.creature_collection_service,
                    "rank_snapshot",
                )
                rankings = rank_snapshot(
                    all_rankings,
                    metric=TopMetric.OVERALL,
                    pokemon_type=normalized_type,
                )
        except ValueError as error:
            await ctx.send(str(error))
            return

        if rankings_service is not None and not all_rankings:
            await ctx.send(
                build_empty_message(
                    type_name=None,
                    shiny_only=False,
                )
            )
            return

        if rankings_service is None and not creatures:
            await ctx.send(
                build_empty_message(
                    type_name=normalized_type,
                    shiny_only=False,
                )
            )
            return

        if rankings_service is None:
            view = CreatureListView(
                author_id=ctx.author.id,
                title=build_top_title(normalized_type),
                entries=[format_creature_entry(creature) for creature in creatures],
            )
        else:

            async def load_rankings(metric, pokemon_type):
                return rank_snapshot(
                    all_rankings,
                    metric=metric,
                    pokemon_type=pokemon_type,
                )

            view = TopCreatureView(
                author_id=ctx.author.id,
                trainer_id=ctx.author.id,
                rankings=rankings,
                metric=TopMetric.OVERALL,
                pokemon_type=normalized_type,
                load_rankings=load_rankings,
            )

        message = await ctx.send(
            embed=view.build_embed(),
            view=view,
        )

        view.message = message
