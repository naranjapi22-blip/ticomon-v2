from discord.ext import commands

from application.bootstrap.core import CoreServices
from interfaces.discord.views.trainer_view import TrainerView


class TrainerCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(name="trainer")
    async def trainer(
        self,
        ctx: commands.Context,
    ):
        view = TrainerView(
            core=self.core,
            trainer_id=ctx.author.id,
        )

        await view.initialize()

        embed = view.build_embed()

        file = view.build_file()

        message = await ctx.send(
            embed=embed,
            file=file,
            view=view,
        )

        view.message = message
