import discord
from discord.ext import commands

from interfaces.discord.application_emojis import get_application_emojis
from interfaces.discord.views.shop_view import ShopView


class ShopCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="shop")
    async def shop(self, ctx: commands.Context) -> None:
        view = ShopView(
            self._core,
            ctx.author.id,
            await get_application_emojis(ctx.bot),
        )
        message = await ctx.send(
            embed=discord.Embed(
                title="TicoMon Shops",
                description="Choose an establishment.",
                color=discord.Color.green(),
            ),
            view=view,
        )
        view.message = message
