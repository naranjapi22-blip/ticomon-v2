from discord.ext import commands

from core.spawn.exceptions import (
    NoActiveSpawnSession,
    NoSelectedOpportunity,
)


class CaptureCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="capture")
    async def capture(self, ctx):
        try:
            result = await self._core.capture_application.capture(
                trainer_id=ctx.author.id,
            )

        except NoActiveSpawnSession:
            await ctx.send("There is no active spawn.")
            return

        except NoSelectedOpportunity:
            await ctx.send("Select a Pokémon before attempting a capture.")
            return

        if result.success:
            await ctx.send(f"✅ You captured {result.creature.species.name}!")
        else:
            await ctx.send("❌ Capture failed!")
