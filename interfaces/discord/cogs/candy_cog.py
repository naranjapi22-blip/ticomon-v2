from discord import Embed
from discord.ext import commands

from application.bootstrap.core import CoreServices

TYPE_EMOJIS = {
    "normal": "<:normal_candy:1526370817967919206>",
    "fire": "<:fire_candy:1526370797713621153>",
    "water": "<:water_candy:1526370800515682404>",
    "electric": "<:electric_candy:1526370799001276446>",
    "grass": "<:grass_candy:1526370801824305322>",
    "ice": "<:ice_candy:1526370811899023461>",
    "fighting": "<:fighting_candy:1526370806299623565>",
    "poison": "<:poison_candy:1526370805515288726>",
    "ground": "<:ground_candy:1526370818635071589>",
    "flying": "<:flying_candy:1526370804063928422>",
    "psychic": "<:psychic_candy:1526370807985471509>",
    "bug": "<:bug_candy:1526370803250237554>",
    "rock": "<:rock_candy:1526370819918528665>",
    "ghost": "<:ghost_candy:1526370810808238211>",
    "dragon": "<:dragon_candy:1526370809713655808>",
    "dark": "<:dark_candy:1526370815430496329>",
    "steel": "<:steel_candy:1526370813396123747>",
    "fairy": "<:fairy_candy:1526370816655102122>",
}


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

                embed.add_field(
                    name=(
                        f"{TYPE_EMOJIS.get(candy_type.value, '🍬')} "
                        f"{candy_type.value.title()}"
                    ),
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
