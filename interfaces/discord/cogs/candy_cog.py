from discord import Embed
from discord.ext import commands

from application.bootstrap.core import CoreServices

TYPE_EMOJI_IDS = {
    "normal": 1526370817967919206,
    "fire": 1526370797713621153,
    "water": 1526370800515682404,
    "electric": 1526370799001276446,
    "grass": 1526370801824305322,
    "ice": 1526370811899023461,
    "fighting": 1526370806299623565,
    "poison": 1526370805515288726,
    "ground": 1526370818635071589,
    "flying": 1526370804063928422,
    "psychic": 1526370807985471509,
    "bug": 1526370803250237554,
    "rock": 1526370819918528665,
    "ghost": 1526370810808238211,
    "dragon": 1526370809713655808,
    "dark": 1526370815430496329,
    "steel": 1526370813396123747,
    "fairy": 1526370816655102122,
}


class CandyCog(commands.Cog):

    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core
        self._application_emojis: dict[int, object] = {}

    async def _get_application_emojis(
        self,
        bot: commands.Bot,
    ) -> dict[int, object]:

        if not self._application_emojis:

            emojis = await bot.fetch_application_emojis()

            self._application_emojis = {emoji.id: emoji for emoji in emojis}

        return self._application_emojis

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

        embed = Embed(
            title="🍬 Your Type Candies",
        )

        if inventory.is_empty():

            embed.description = "You don't have any candies yet."

        else:

            application_emojis = await self._get_application_emojis(
                ctx.bot,
            )

            total = 0

            for candy_type, amount in sorted(
                inventory.items(),
                key=lambda item: item[0].value,
            ):

                emoji_id = TYPE_EMOJI_IDS.get(
                    candy_type.value,
                )

                emoji = application_emojis.get(
                    emoji_id,
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
