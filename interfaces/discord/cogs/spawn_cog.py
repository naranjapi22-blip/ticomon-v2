import discord
from discord.ext import commands

from core.spawn.application.spawn_application_service import (
    SpawnAlreadyActive,
)
from interfaces.discord.views.spawn_view import SpawnView
from rendering.spawn_preview import generate_spawn_preview


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

        preview = generate_spawn_preview(
            session.opportunities,
        )

        await ctx.send(
            content="**A wild spawn appeared!**",
            file=discord.File(
                preview,
                filename="spawn.png",
            ),
            view=SpawnView(
                self._core,
                session,
            ),
        )
