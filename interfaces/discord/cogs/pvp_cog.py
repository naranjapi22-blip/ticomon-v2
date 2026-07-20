import discord
from discord.ext import commands

from interfaces.discord.views.pvp_challenge_view import PvpChallengeView


class PvpCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="pvp")
    async def pvp(self, ctx: commands.Context, opponent: discord.Member) -> None:
        if opponent.bot:
            await ctx.send("You cannot challenge a bot to PvP.")
            return
        for trainer_id in (ctx.author.id, opponent.id):
            creatures = await self._core.creature_repository.get_by_trainer(trainer_id)
            if len(creatures) < 3:
                await ctx.send(
                    f"Trainer <@{trainer_id}> needs at least three creatures for PvP."
                )
                return
        try:
            session = self._core.pvp_application_service.challenge(
                ctx.author.id,
                opponent.id,
            )
        except ValueError as error:
            await ctx.send(f"PvP challenge unavailable: {error}")
            return
        view = PvpChallengeView(self._core, session)
        message = await ctx.send(
            f"<@{ctx.author.id}> challenged <@{opponent.id}> to fast PvP.",
            view=view,
        )
        view.message = message

    @pvp.error
    async def pvp_error(self, ctx: commands.Context, error) -> None:
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("Usage: `!pvp @trainer`")
            return
        raise error
