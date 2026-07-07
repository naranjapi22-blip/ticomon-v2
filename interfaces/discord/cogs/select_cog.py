from discord.ext import commands

from core.spawn.exceptions import NoActiveSpawnSession


class SelectCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="select")
    async def select(self, ctx, index: int):
        try:
            opportunity = (
                await (
                    self._core.select_opportunity_application.select_opportunity(
                        opportunity_index=index,
                    )
                )
            )

        except NoActiveSpawnSession:
            await ctx.send("There is no active spawn.")
            return

        await ctx.send(f"You selected {opportunity.species.name}.")
