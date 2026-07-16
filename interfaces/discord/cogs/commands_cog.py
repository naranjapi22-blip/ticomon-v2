import discord
from discord.ext import commands


class CommandsCog(commands.Cog):
    @commands.command(name="commands")
    async def commands_command(self, ctx: commands.Context):
        """Displays the available commands."""

        embed = discord.Embed(
            title="📖 TicoMon Commands",
            description=(
                "Welcome to **TicoMon**!\n"
                "Use these commands to begin your adventure."
            ),
            color=discord.Color.green(),
        )

        embed.add_field(
            name="📖 Collection",
            value=(
                "`!pokedex` — View your Pokédex.\n"
                "`!pokedex caught|missing`\n"
                "`!pokedex type <type>`\n"
                "`!pokedex gen <generation>`\n"
                "`!pokedex legendary|mythical`\n"
                "`!info <pokemon>` — Pokémon information.\n"
                "`!ivs [pokemon]` — View your Pokémon IVs.\n"
                "`!top [type]` — View your top Pokémon.\n"
                "`!inventory [type|shiny]` — View recent Pokémon.\n"
                "`!duplicates [pokemon/type]` — Find duplicate Pokémon."
            ),
            inline=False,
        )

        embed.add_field(
            name="⚔️ Gameplay",
            value=(
                "`!spawn` — Encounter wild Pokémon.\n"
                "`!energy` — Check your Energy.\n"
                "`!evolve` — Evolve your Pokémon.\n"
                "`!mint <collection_number>` — Change a Pokémon's nature effect.\n"
                "`!release` — Release Pokémon for rewards.\n"
                "`!safari` — Start or join a Safari expedition.\n"
                "`!trade @trainer <collection_number>` — "
                "Trade one Pokémon with another trainer."
            ),
            inline=False,
        )

        embed.add_field(
            name="👤 Trainer",
            value=(
                "`!profile` — View your trainer profile.\n"
                "`!achievements` — View your achievement progress.\n"
                "`!trainer` — Choose your trainer.\n"
                "`!favorite` — Select your featured Pokémon."
            ),
            inline=False,
        )

        embed.add_field(
            name="🎲 Inventory",
            value="`!candies` — View your Candy inventory.",
            inline=False,
        )

        embed.set_footer(text="More features are coming during the Beta!")

        await ctx.send(embed=embed)
