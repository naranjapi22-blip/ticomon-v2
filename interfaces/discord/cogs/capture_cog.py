from discord.ext import commands

from core.spawn.exceptions import NoActiveSpawnSession


class CaptureCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="capture")
    async def capture(self, ctx, index: int):
        try:
            result = await self._core.capture_application.capture(
                trainer_id=ctx.author.id,
                opportunity_index=index,
            )

        except NoActiveSpawnSession:
            await ctx.send("There is no active spawn.")
            return

        if result.success:
            await ctx.send(f"✅ You captured {result.creature.species.name}!")
        else:
            await ctx.send("❌ Capture failed!")
