import logging

import discord
from discord.ext import commands

from application.bootstrap.core import CoreServices
from core.creature.stat import Stat
from interfaces.discord.images import (
    download_gif_file,
    get_creature_gif,
)

logger = logging.getLogger(__name__)

STAT_LABELS = {
    Stat.HP: ("❤️", "HP"),
    Stat.ATTACK: ("⚔️", "Atk"),
    Stat.DEFENSE: ("🛡️", "Def"),
    Stat.SP_ATTACK: ("🔮", "SpA"),
    Stat.SP_DEFENSE: ("✨", "SpD"),
    Stat.SPEED: ("⚡", "Spe"),
}


class IVsCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(name="ivs")
    async def ivs(
        self,
        ctx: commands.Context,
        collection_number: int,
    ):
        try:
            creature = await self.core.creature_info_service.get_creature(
                trainer_id=ctx.author.id,
                collection_number=collection_number,
            )

        except ValueError:
            await ctx.send(
                "❌ You don't own a creature with collection number "
                f"**{collection_number}**."
            )
            return

        embed = discord.Embed(
            title=creature.species.name.title(),
            color=(
                discord.Color.gold() if creature.is_shiny else discord.Color.green()
            ),
        )

        lines = [
            "📊 **Stats (Lvl 50 | IVs)**",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        effective_nature = getattr(creature, "effective_nature", creature.nature)

        for stat in Stat:
            stat_value = self.core.stat_calculator.calculate(
                creature,
                stat,
            )

            iv = creature.iv_for(stat)

            emoji, label = STAT_LABELS[stat]
            arrow = effective_nature.arrow_for(stat)

            lines.append(
                f"{emoji} **{label}** " f"`{stat_value:>3}{arrow} │ {iv:>2}/31`"
            )

        lines.extend(
            [
                "",
                "📝 **Details**",
                "━━━━━━━━━━━━━━━━━━━━",
                f"🆔 **Collection:** #{creature.collection_number}",
                f"📊 **IV Total:** {creature.iv_percentage}%",
                f"📏 **Size:** {creature.size}",
                f"🍃 **Nature:** {effective_nature}",
                *(
                    [f"🌱 **Original nature:** {creature.nature}"]
                    if getattr(creature, "minted_nature", None) is not None
                    else []
                ),
                f"✨ **Shiny:** {'Yes' if creature.is_shiny else 'No'}",
            ]
        )

        embed.description = "\n".join(lines)

        gif_url = get_creature_gif(creature)

        try:
            gif_file = await download_gif_file(
                gif_url,
                "ivs.gif",
            )
        except Exception:
            logger.warning(
                "Unable to attach creature GIF command=%s species=%s",
                "ivs",
                creature.species.name,
            )
            await ctx.send(embed=embed)
            return

        embed.set_image(url="attachment://ivs.gif")

        await ctx.send(
            embed=embed,
            file=gif_file,
        )
