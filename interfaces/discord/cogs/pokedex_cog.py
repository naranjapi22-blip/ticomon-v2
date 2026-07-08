from discord.ext import commands

from application.bootstrap.core import CoreServices
from application.pokedex.filter import PokedexFilter
from interfaces.discord.views.pokedex_view import PokedexView


class PokedexCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(name="pokedex")
    async def pokedex(
        self,
        ctx: commands.Context,
        *args: str,
    ):
        args = [arg.lower() for arg in args]

        filter = PokedexFilter()

        if "caught" in args:
            filter.discovered = True

        if "missing" in args:
            filter.discovered = False

        if "legendary" in args:
            filter.legendary = True

        if "mythical" in args:
            filter.mythical = True

        if len(args) >= 2:

            if args[0] == "type":
                filter.pokemon_type = args[1]

            elif args[0] == "gen":

                try:
                    filter.generation = int(args[1])

                except ValueError:
                    await ctx.send("❌ Generation must be a number.")
                    return

        view = PokedexView(
            core=self.core,
            trainer_id=ctx.author.id,
            filter=filter,
        )

        await view.initialize()

        embed, file = await view._render_page()

        message = await ctx.send(
            embed=embed,
            file=file,
            view=view,
        )

        view.message = message
