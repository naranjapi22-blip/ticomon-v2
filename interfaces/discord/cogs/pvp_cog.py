import logging

import discord
from discord.ext import commands

from interfaces.discord.activity.pvptest_registry import PvptestActivityRegistry
from interfaces.discord.views.pvp_challenge_view import PvpChallengeView

logger = logging.getLogger(__name__)


class PvpCog(commands.Cog):
    def __init__(
        self, core, activity_registry: PvptestActivityRegistry | None = None
    ) -> None:
        self._core = core
        self._activity_registry = activity_registry

    @commands.command(name="pvp")
    async def pvp(self, ctx: commands.Context, opponent: discord.Member) -> None:
        await self._start_challenge(ctx, opponent)

    @commands.command(name="pvptest")
    async def pvptest(self, ctx: commands.Context, opponent: discord.Member) -> None:
        if self._activity_registry is None:
            await ctx.send("The experimental PvP Activity is not enabled.")
            return
        await self._start_challenge(ctx, opponent, activity_mode=True)

    async def _start_challenge(
        self,
        ctx: commands.Context,
        opponent: discord.Member,
        *,
        activity_mode: bool = False,
    ) -> None:
        if opponent.bot:
            await ctx.send("You cannot challenge a bot to PvP.")
            return
        if activity_mode and self._activity_registry.find_for_channel(ctx.channel.id):
            await ctx.send(
                "An experimental PvP Activity is already active in this channel."
            )
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

        on_activity_ready = None
        on_activity_finished = None
        if activity_mode:
            on_activity_ready = self._make_activity_ready_callback(
                ctx, session, opponent
            )
            on_activity_finished = self._make_activity_finished_callback(session)
        view = PvpChallengeView(
            self._core,
            session,
            display_names={
                ctx.author.id: ctx.author.display_name,
                opponent.id: opponent.display_name,
            },
            activity_registry=self._activity_registry if activity_mode else None,
            on_activity_ready=on_activity_ready,
            on_activity_finished=on_activity_finished,
        )
        message = await ctx.send(
            (
                f"<@{ctx.author.id}> challenged <@{opponent.id}> to "
                "experimental PvP Activity."
                if activity_mode
                else f"<@{ctx.author.id}> challenged <@{opponent.id}> to fast PvP."
            ),
            view=view,
        )
        view.message = message

    def _make_activity_ready_callback(self, ctx, session, opponent):
        async def on_ready(team_view) -> None:
            display_names = {
                ctx.author.id: ctx.author.display_name,
                opponent.id: opponent.display_name,
            }

            async def public_status(status: str) -> None:
                if team_view.message is None:
                    return
                try:
                    await team_view.message.edit(
                        content=(
                            f"{display_names[ctx.author.id]} vs. "
                            f"{display_names[opponent.id]}\n"
                            "Both teams are ready.\n\n"
                            "Launch the TicoMon Activity from this channel.\n"
                            "Both players must join the same Activity instance.\n\n"
                            f"{status}"
                        ),
                        view=None,
                    )
                except discord.HTTPException:
                    logger.debug(
                        "Unable to update experimental Activity status", exc_info=True
                    )

            async def public_result(result: str) -> None:
                await ctx.send(result)

            try:
                await self._activity_registry.bind(
                    session_id=session.id,
                    guild_id=ctx.guild.id if ctx.guild else None,
                    channel_id=ctx.channel.id,
                    player_ids=(ctx.author.id, opponent.id),
                    display_names=display_names,
                    public_status=public_status,
                    public_result=public_result,
                )
            except Exception:
                await self._core.pvp_application_service.cleanup(session.id)
                raise
            await public_status("Activity status: 0/2 connected")

        return on_ready

    def _make_activity_finished_callback(self, session):
        async def on_finished(team_view, battle) -> None:
            await self._activity_registry.handle_finished(session.id, battle)
            current = self._core.pvp_application_service.registry.get(session.id)
            winner = current.final_winner_id
            winner_name = (
                team_view.display_names.get(winner, "Unknown trainer")
                if winner is not None
                else "No winner"
            )
            reason = current.final_reason or ("tie" if current.final_tie else "normal")
            if team_view.message is not None:
                await team_view.message.edit(
                    content=(
                        "Experimental Activity PvP finished.\n"
                        f"Winner: {winner_name}\n"
                        f"Reason: {reason}."
                    ),
                    view=None,
                )

        return on_finished

    @pvp.error
    async def pvp_error(self, ctx: commands.Context, error) -> None:
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("Usage: `!pvp @trainer`")
            return
        raise error

    @pvptest.error
    async def pvptest_error(self, ctx: commands.Context, error) -> None:
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("Usage: `!pvptest @trainer`")
            return
        raise error
