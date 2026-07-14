import logging

from discord import Embed
from discord.ext import commands

from application.bootstrap.core import CoreServices

logger = logging.getLogger(__name__)


class CandyCog(commands.Cog):

    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(
        name="candies",
    )
    async def candies(
        self,
        ctx: commands.Context,
    ):

        inventory = await self.core.candy_repository.get(
            trainer_id=ctx.author.id,
        )

        application_emojis = await ctx.bot.fetch_application_emojis()
        logger.debug(
            "fetched application emojis application_id=%s count=%s",
            ctx.bot.application_id,
            len(application_emojis),
        )

        emojis_by_name = {emoji.name: emoji for emoji in application_emojis}

        embed = Embed(
            title="🍬 Your Type Candies",
        )

        if inventory.is_empty():

            embed.description = "You don't have any candies yet."

        else:

            total = 0

            for candy_type, amount in sorted(
                inventory.items(),
                key=lambda item: item[0].value,
            ):

                emoji_name = f"{candy_type.value}_candy"

                emoji = emojis_by_name.get(
                    emoji_name,
                )

                emoji_text = str(emoji) if emoji is not None else "🍬"

                embed.add_field(
                    name=(f"{emoji_text} " f"{candy_type.value.title()}"),
                    value=f"x{amount}",
                    inline=True,
                )

                total += amount

            embed.set_footer(
                text=f"Total Candies: {total}",
            )

        await ctx.send(
            embed=embed,
        )
