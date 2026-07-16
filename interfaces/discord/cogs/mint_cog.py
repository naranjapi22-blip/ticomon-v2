from discord.ext import commands

from interfaces.discord.views.nature_mint_view import NatureMintView


class MintCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="mint")
    async def mint(self, ctx, collection_number: int) -> None:
        try:
            preview = await self._core.nature_mint_application.preview(
                ctx.author.id,
                collection_number,
            )
        except ValueError as error:
            await ctx.send(str(error))
            return

        creature = preview.creature
        view = NatureMintView(
            self._core,
            ctx.author.id,
            collection_number,
            preview,
        )
        await ctx.send(
            embed=view._embed(
                f"You have **{preview.mint_amount} Nature Mints**.\n\n"
                f"Use 1 Nature Mint on **{creature.species.name.title()} "
                f"(#{creature.collection_number})**?\n\n"
                f"Original nature: **{creature.nature}**\n"
                f"Current effect: **{creature.effective_nature}**"
            ),
            view=view,
        )
