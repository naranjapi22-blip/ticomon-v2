from discord.ext import commands

from interfaces.discord.application_emojis import get_application_emojis
from interfaces.discord.views.collections_view import CollectionsOverviewView


class CollectionsCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="collections")
    async def collections(self, ctx: commands.Context) -> None:
        try:
            albums = await self._core.collection_application.albums(ctx.author.id)
        except ValueError as error:
            await ctx.send(str(error))
            return
        view = CollectionsOverviewView(
            self._core,
            ctx.author.id,
            albums,
            await get_application_emojis(ctx.bot),
        )
        message = await ctx.send(embed=view.embed(), view=view)
        view.message = message
