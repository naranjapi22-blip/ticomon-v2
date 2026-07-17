import logging
import os

import discord
from discord.ext import commands

from application.bootstrap.core import CoreServices
from core.creature.stat import Stat
from interfaces.discord.images import get_species_gif
from interfaces.discord.input_normalizer import normalize_text

logger = logging.getLogger(__name__)


class InfoCog(commands.Cog):
    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(name="info")
    async def info(
        self,
        ctx: commands.Context,
        *,
        pokemon: str,
    ):
        try:
            species_info = await self.core.species_info_service.get_species_info(
                trainer_id=ctx.author.id,
                species_name=normalize_text(pokemon),
            )
        except ValueError as error:
            await ctx.send(f"❌ {error}")
            return

        species = species_info.species
        creatures = species_info.creatures

        embed = discord.Embed(
            title=species.name.title(),
            color=discord.Color.green(),
        )

        gif_url = get_species_gif(
            species_id=species.pokeapi_id,
            shiny=False,
        )

        types = " / ".join(pokemon_type.title() for pokemon_type in species.types)

        first_capture = creatures[0].collection_number if creatures else None

        collection_ids = ", ".join(
            f"#{creature.collection_number}" for creature in creatures
        )

        stats = species.base_stats

        base_stats = (
            f"❤️ **HP:** {stats.for_stat(Stat.HP)}\n"
            f"⚔️ **Attack:** {stats.for_stat(Stat.ATTACK)}\n"
            f"🛡️ **Defense:** {stats.for_stat(Stat.DEFENSE)}\n"
            f"✨ **Sp. Attack:** {stats.for_stat(Stat.SP_ATTACK)}\n"
            f"🧠 **Sp. Defense:** {stats.for_stat(Stat.SP_DEFENSE)}\n"
            f"⚡ **Speed:** {stats.for_stat(Stat.SPEED)}"
        )

        embed.add_field(
            name="📋 General Information",
            value=(
                f"✨ **Type:** {types}\n"
                f"📅 **First Capture:** "
                f"{f'#{first_capture}' if first_capture else '—'}\n"
                f"🔢 **Total Caught:** {len(creatures)}\n"
                f"🆔 **Collection IDs:** "
                f"{collection_ids if collection_ids else '—'}\n"
                f"📏 **Height:** {species.height / 10:.1f} m\n"
                f"⚖️ **Weight:** {species.weight / 10:.1f} kg"
            ),
            inline=False,
        )

        embed.add_field(
            name="📊 Base Stats",
            value=base_stats,
            inline=False,
        )

        embed.set_image(url=gif_url)

        sent_message = await ctx.send(embed=embed)

        if os.getenv("GIF_PROXY_DEBUG", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            try:
                fetched_message = await sent_message.channel.fetch_message(
                    sent_message.id
                )
                fetched_embed = (
                    fetched_message.embeds[0] if fetched_message.embeds else None
                )

                if fetched_embed is not None and fetched_embed.image is not None:
                    logger.info(
                        (
                            "info_gif_proxy_debug embed_image_url=%s "
                            "proxy_url=%s width=%s height=%s"
                        ),
                        fetched_embed.image.url,
                        fetched_embed.image.proxy_url,
                        fetched_embed.image.width,
                        fetched_embed.image.height,
                    )
            except Exception:
                logger.exception("info_gif_proxy_debug failed")
