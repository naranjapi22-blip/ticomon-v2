import discord
from discord.ext import commands


class CommandsCog(commands.Cog):
    @commands.command(name="commands")
    async def commands_command(self, ctx: commands.Context):
        """Displays the available commands."""
        embed = discord.Embed(
            title="TicoMon Commands",
            description=(
                "Welcome to **TicoMon**!\nUse these commands to begin your adventure."
            ),
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Collection",
            value=(
                "`!pokedex` - View your Pokedex.\n"
                "`!pokedex caught|missing`\n"
                "`!pokedex type <type>`\n"
                "`!pokedex gen <generation>`\n"
                "`!pokedex legendary|mythical`\n"
                "`!info <pokemon>` - Pokemon information.\n"
                "`!ivs [pokemon]` - View your Pokemon IVs.\n"
                "`!top [type]` - View your top Pokemon.\n"
                "`!inventory [type|shiny]` - View recent Pokemon.\n"
                "`!duplicates [pokemon/type]` - Find duplicate Pokemon."
            ),
            inline=False,
        )
        embed.add_field(
            name="Gameplay",
            value=(
                "`!spawn` - Encounter wild Pokemon.\n"
                "`!energy` - Check your Energy.\n"
                "`!evolve` - Evolve your Pokemon.\n"
                "`!mint <collection_number>` - Use a Nature Mint. The original "
                "nature stays intact; a mint is consumed only after confirming "
                "a valid change.\n"
                "`!release` - Release Pokemon for rewards.\n"
                "`!safari` - Start or join a Safari expedition.\n"
                "`!trade @trainer <collection_number>` - Trade one Pokemon.\n"
                "`!shop` - Spend type-specific candies on special creatures."
            ),
            inline=False,
        )
        embed.add_field(
            name="Trainer",
            value=(
                "`!profile` - View your trainer profile.\n"
                "`!achievements` - View achievement progress.\n"
                "`!trainer` - Choose your trainer.\n"
                "`!favorite` - Select your featured Pokemon."
            ),
            inline=False,
        )
        embed.add_field(
            name="Inventory",
            value="`!candies` - View your Candy inventory.",
            inline=False,
        )
        embed.set_footer(text="More features are coming during the Beta!")
        await ctx.send(embed=embed)
