from datetime import UTC, datetime

import discord
from discord.ext import commands

from application.battle.exceptions import BattleNotFound
from core.battle.exceptions import InsufficientTeamSize, SameBattleParticipant
from interfaces.discord.views.battle_gif_challenge_view import (
    BattleGifChallengeView,
)


class BattleGifExperimentCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="batallagif")
    async def batalla_gif(
        self,
        ctx: commands.Context,
        opponent: discord.Member,
    ) -> None:
        if opponent.bot:
            await ctx.send("❌ You cannot battle a bot.")
            return

        try:
            battle = await self._core.battle_application_service.create_challenge(
                initiator_trainer_id=ctx.author.id,
                opponent_trainer_id=opponent.id,
                created_at=datetime.now(UTC),
            )
        except SameBattleParticipant:
            await ctx.send("❌ You cannot battle yourself.")
            return
        except InsufficientTeamSize as error:
            await ctx.send(f"❌ {error}")
            return
        except BattleNotFound:
            await ctx.send("❌ Battle could not be created.")
            return

        if battle.id is None:
            await ctx.send("❌ Battle could not be created.")
            return

        view = BattleGifChallengeView(
            self._core,
            battle.id,
            ctx.author.id,
            opponent.id,
        )
        message = await ctx.send(embed=view.build_embed(battle), view=view)
        view.message = message

    @batalla_gif.error
    async def batalla_gif_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "opponent":
                await ctx.send("Usage: `!batallagif @trainer`")
                return
        if isinstance(error, commands.BadArgument):
            await ctx.send("Usage: `!batallagif @trainer`")
            return
        raise error
