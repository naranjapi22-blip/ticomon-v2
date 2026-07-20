from discord.ext import commands

from interfaces.discord.views.moves_view import MoveLoadoutView, render_loadout


class MovesCog(commands.Cog):
    """Displays and privately edits a creature's persistent PvP moveset."""

    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="moves")
    async def moves(self, ctx, collection_number: int) -> None:
        if self._core.pvp_application_service.registry.is_occupied(ctx.author.id):
            await ctx.send("You cannot edit moves during an active PvP challenge.")
            return
        try:
            loadout = await self._core.creature_loadout_service.get_loadout(
                ctx.author.id, collection_number
            )
        except ValueError:
            await ctx.send(f"You do not own creature #{collection_number}.")
            return

        view = MoveLoadoutView(
            self._core.creature_loadout_service,
            loadout,
            owner_id=ctx.author.id,
        )
        try:
            view.message = await ctx.author.send(render_loadout(loadout), view=view)
        except Exception:
            await ctx.send("I could not open a private moves editor for you.")

    @moves.error
    async def moves_error(self, ctx, error) -> None:
        if isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send("Usage: !moves <collection_number>")
            return
        raise error
