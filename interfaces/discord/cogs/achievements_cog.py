from discord.ext import commands

from interfaces.discord.views.achievements_view import AchievementsView


class AchievementsCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="achievements")
    async def achievements(self, ctx) -> None:
        statuses = await self._core.achievement_query_service.get_for_trainer(
            ctx.author.id
        )
        view = AchievementsView(ctx.author.id, statuses)
        view.message = await ctx.send(embed=view.build_embed(), view=view)
