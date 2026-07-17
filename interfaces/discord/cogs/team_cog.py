from discord.ext import commands

from application.bootstrap.core import CoreServices
from interfaces.discord.views.team_launcher_view import TeamLauncherView


class TeamCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ) -> None:
        self._core = core

    @commands.command(name="team")
    async def team(
        self,
        ctx: commands.Context,
    ) -> None:
        view = TeamLauncherView(
            self._core,
            ctx.author.id,
        )

        view.message = await ctx.send(
            "Click **Open Team** to manage your team privately.",
            view=view,
        )
