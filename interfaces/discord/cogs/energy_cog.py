from datetime import UTC, datetime

from discord.ext import commands


class EnergyCog(commands.Cog):

    def __init__(self, core):
        self._core = core

    @commands.command(name="energy")
    async def energy(self, ctx):

        try:
            energy = await self._core.energy_service.get(
                ctx.author.id,
            )

        except ValueError:
            await ctx.send(
                "🌱 You haven't started your adventure yet.\n"
                "Choose your starter Pokémon to begin your journey."
            )
            return

        if energy.current_energy >= energy.max_energy:

            await ctx.send(
                f"⚡ Energy: {energy.current_energy}/{energy.max_energy}\n"
                "Energy is full.",
            )

            return

        elapsed_seconds = int(
            (datetime.now(UTC) - energy.last_regenerated_at).total_seconds()
        )

        remaining_seconds = 3600 - (elapsed_seconds % 3600)

        if remaining_seconds == 3600:
            remaining_seconds = 0

        minutes, seconds = divmod(
            remaining_seconds,
            60,
        )

        await ctx.send(
            f"⚡ Energy: {energy.current_energy}/{energy.max_energy}\n"
            f"Next energy in {minutes}m {seconds}s.",
        )
