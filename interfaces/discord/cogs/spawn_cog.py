from discord.ext import commands

from core.spawn.application.spawn_application_service import (
    SpawnAlreadyActive,
)
from interfaces.discord.views.spawn_view import SpawnView


class SpawnCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="spawn")
    async def spawn(self, ctx):
        try:
            session = await self._core.spawn_application.spawn(
                guild_id=ctx.guild.id,
                owner_id=ctx.author.id,
            )
        except SpawnAlreadyActive:
            await ctx.send(
                "Ya existe un !spawn activo en este servidor.",
            )
            return

        lines = ["Spawn:\n"]

        for index, opportunity in enumerate(
            session.opportunities,
            start=1,
        ):
            lines.append(
                f"{index}. "
                f"{opportunity.species.name} "
                f"({opportunity.species.spawn_rarity.name})"
            )

        await ctx.send(
            "\n".join(lines),
            view=SpawnView(
                self._core,
                session,
            ),
        )
