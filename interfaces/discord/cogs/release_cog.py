from discord.ext import commands

from application.release.exceptions import ReleaseCreatureAssignedToTeam
from interfaces.discord.release_messages import assigned_creatures_message
from interfaces.discord.views.release_confirm_view import (
    ReleaseConfirmView,
)


class ReleaseCog(commands.Cog):

    def __init__(
        self,
        core,
    ):
        self._core = core

    @commands.command(
        name="release",
    )
    async def release(
        self,
        ctx,
        *collection_numbers: int,
    ):

        if not collection_numbers:

            await ctx.send(
                "❌ You must provide at least one collection number.",
            )

            return

        try:

            preview = await self._core.preview_release_application.preview(
                trainer_id=ctx.author.id,
                collection_numbers=list(collection_numbers),
            )

        except ReleaseCreatureAssignedToTeam as error:

            await ctx.send(
                await assigned_creatures_message(self._core, ctx.author.id, error),
            )

            return

        except ValueError:

            await ctx.send(
                "❌ One or more collection numbers are invalid.",
            )

            return

        released = "\n".join(
            f"• #{creature.collection_number} " f"{creature.species.name.title()}"
            for creature in preview.creatures
        )

        rewards = "\n".join(
            f"• {amount} {candy_type.value.title()} Candy"
            for candy_type, amount in preview.reward_bundle.items()
        )

        view = ReleaseConfirmView(
            core=self._core,
            trainer_id=ctx.author.id,
            collection_numbers=list(collection_numbers),
        )

        await ctx.send(
            (
                "## Release Preview\n\n"
                "**The following Pokémon will be released:**\n\n"
                f"{released}\n\n"
                "**Rewards:**\n"
                f"{rewards}\n\n"
                "Do you want to continue?"
            ),
            view=view,
        )
