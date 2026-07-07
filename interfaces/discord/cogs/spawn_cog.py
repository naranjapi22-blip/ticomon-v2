from discord.ext import commands


class SpawnCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="spawn")
    async def spawn(self, ctx):
        opportunities = await self._core.spawn_application.spawn()

        lines = ["Spawn:\n"]

        for index, opportunity in enumerate(opportunities, start=1):
            lines.append(
                f"{index}. "
                f"{opportunity.species.name} "
                f"({opportunity.species.spawn_rarity.name})"
            )

        await ctx.send("\n".join(lines))
