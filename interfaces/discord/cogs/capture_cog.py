from discord.ext import commands

from core.spawn.exceptions import (
    NoActiveSpawnSession,
    NoSelectedOpportunity,
)
from interfaces.discord.achievement_notifications import send_unlocks
from interfaces.discord.application_emojis import (
    candy_emoji_prefix,
    get_application_emojis,
    species_emoji_from_index,
)


class CaptureCog(commands.Cog):
    def __init__(self, core):
        self._core = core

    @commands.command(name="capture")
    async def capture(self, ctx):
        try:
            result = await self._core.capture_application.capture(
                trainer_id=ctx.author.id,
                guild_id=ctx.guild.id,
            )

        except NoActiveSpawnSession:
            await ctx.send("There is no active spawn.")
            return

        except NoSelectedOpportunity:
            await ctx.send("Select a Pokémon before attempting a capture.")
            return

        if result.success:

            emojis = await get_application_emojis(ctx.bot)
            species_emoji = species_emoji_from_index(
                emojis,
                result.creature.species.pokeapi_id,
            )

            rewards = "\n".join(
                f"{candy_emoji_prefix(emojis, candy_type)}"
                f"{candy_type.value.title()}: +{amount}"
                for candy_type, amount in result.reward.items()
            )

            await ctx.send(
                f"✅ You captured {species_emoji + ' ' if species_emoji else ''}"
                f"{result.creature.species.name}!\n\n{rewards}"
            )
            await send_unlocks(
                ctx.send,
                result.achievements,
                context="capture",
                bot=ctx.bot,
            )
        else:
            await ctx.send("❌ Capture failed!")
