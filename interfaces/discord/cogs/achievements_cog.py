from discord.ext import commands

from interfaces.discord.application_emojis import get_application_emojis
from interfaces.discord.views.achievements_view import AchievementsView


class AchievementsCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="achievements")
    async def achievements(self, ctx) -> None:
        statuses = await self._core.achievement_query_service.get_for_trainer(
            ctx.author.id
        )
        view = AchievementsView(
            ctx.author.id,
            statuses,
            await get_application_emojis(ctx.bot),
        )
        view.message = await ctx.send(embed=view.build_embed(), view=view)
