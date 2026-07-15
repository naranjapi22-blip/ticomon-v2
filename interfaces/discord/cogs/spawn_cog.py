import discord
from discord.ext import commands

from core.energy.exceptions import (
    NotEnoughEnergyException,
)
from core.spawn.application.spawn_application_service import (
    SpawnAlreadyActive,
)
from interfaces.discord.views.spawn_view import SpawnView
from interfaces.discord.views.starter_view import StarterView
from rendering.spawn_preview import generate_spawn_preview


class SpawnCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="spawn")
    async def spawn(self, ctx):
        trainer_exists = await self._core.trainer_repository.exists(
            ctx.author.id,
        )

        if not trainer_exists:

            view = StarterView(
                core=self._core,
                trainer_id=ctx.author.id,
            )

            await view.initialize()

            message = await ctx.send(
                embed=view.build_embed(),
                view=view,
            )

            view.message = message

            return

        try:
            await self._core.energy_service.consume(
                ctx.author.id,
            )

            session = await self._core.spawn_application.spawn(
                guild_id=ctx.guild.id,
                owner_id=ctx.author.id,
            )

        except NotEnoughEnergyException:
            await ctx.send(
                "You don't have enough energy.",
            )
            return

        except SpawnAlreadyActive:
            await ctx.send(
                "There is already an active !spawn in this server.",
            )
            return

        preview = generate_spawn_preview(
            session.opportunities,
        )
        embed = discord.Embed(
            description="**A wild spawn appeared!**",
        )
        embed.set_image(
            url="attachment://spawn.png",
        )

        await ctx.send(
            embed=embed,
            file=discord.File(
                preview,
                filename="spawn.png",
            ),
            view=SpawnView(
                self._core,
                session,
            ),
        )
