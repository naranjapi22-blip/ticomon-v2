import logging

import discord
from discord.ext import commands

from application.bootstrap.core import CoreServices
from interfaces.discord.images import (
    download_gif_file,
    get_creature_gif,
)

logger = logging.getLogger(__name__)


class ProfileCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(name="profile")
    async def profile(
        self,
        ctx: commands.Context,
        member: discord.Member | None = None,
    ):
        trainer = member or ctx.author

        profile = await self.core.profile_service.get_profile(
            trainer.id,
        )

        embed = discord.Embed(
            title=f"🎒 Trainer Card: {trainer.display_name}",
            color=discord.Color.green(),
        )

        embed.set_thumbnail(
            url=trainer.display_avatar.url,
        )

        embed.add_field(
            name="📊 Collection Statistics",
            value=(
                f"• **Total caught:** `{profile.total_captured}`\n"
                f"• **Shiny ✨:** `{profile.shiny_count}`"
            ),
            inline=False,
        )

        blocks = int(profile.completion_percentage // 10)
        progress_bar = "🟩" * blocks + "⬛" * (10 - blocks)

        embed.add_field(
            name="📈 Pokédex Progress",
            value=(
                f"{progress_bar}\n"
                f"**{profile.completion_percentage:.1f}%**\n"
                f"`{profile.unique_species}` of `1077` registered."
            ),
            inline=False,
        )

        if profile.featured_creature is None:
            embed.add_field(
                name="🌟 Featured Partner",
                value="*No featured Pokémon yet.*",
                inline=False,
            )
        else:
            embed.add_field(
                name="🌟 Featured Partner",
                value=(
                    f"**{profile.featured_creature.species.name.title()}**"
                    f"{' ✨' if profile.featured_creature.is_shiny else ''}"
                ),
                inline=False,
            )

            if profile.featured_creature.is_shiny:
                embed.color = discord.Color.gold()

            gif_url = get_creature_gif(
                profile.featured_creature,
            )

            try:
                gif_file = await download_gif_file(
                    gif_url,
                    "profile.gif",
                )
            except Exception:
                logger.warning(
                    "Unable to attach creature GIF command=%s species=%s",
                    "profile",
                    profile.featured_creature.species.name,
                )
            else:
                embed.set_image(
                    url="attachment://profile.gif",
                )

                await ctx.send(
                    embed=embed,
                    file=gif_file,
                )
                return

        await ctx.send(embed=embed)

    @commands.command(name="favorite")
    async def favorite(
        self,
        ctx: commands.Context,
        collection_number: int,
    ):
        await self.core.profile_service.set_featured_creature(
            trainer_id=ctx.author.id,
            collection_number=collection_number,
        )

        await ctx.send(
            f"⭐ Creature #{collection_number} is now your featured partner."
        )
