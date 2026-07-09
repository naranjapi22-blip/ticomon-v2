from discord.ext import commands

from interfaces.discord.views.evolution_confirm_view import (
    EvolutionConfirmView,
)
from interfaces.discord.views.evolution_view import (
    EvolutionView,
)


class EvolutionCog(commands.Cog):

    def __init__(
        self,
        core,
    ):
        self._core = core

    @commands.command(
        name="evolve",
    )
    async def evolve(
        self,
        ctx,
        collection_number: int,
    ):

        try:

            options = await self._core.evolution_application.get_options(
                trainer_id=ctx.author.id,
                collection_number=collection_number,
            )

        except ValueError:

            await ctx.send(
                "❌ You don't have a Pokémon with that collection number.",
            )

            return

        if not options:

            await ctx.send(
                "❌ This Pokémon cannot evolve.",
            )

            return

        if len(options) > 1:

            view = await EvolutionView(
                core=self._core,
                trainer_id=ctx.author.id,
                collection_number=collection_number,
                options=options,
            ).build()

            await ctx.send(
                "✨ Choose your evolution:",
                view=view,
            )

            return

        rule = options[0]

        confirmation = await self._core.evolution_application.get_confirmation(
            trainer_id=ctx.author.id,
            collection_number=collection_number,
            rule=rule,
        )

        emoji = {
            "normal": "⚪",
            "fire": "🔥",
            "water": "💧",
            "electric": "⚡",
            "grass": "🌿",
            "ice": "❄️",
            "fighting": "🥊",
            "poison": "☠️",
            "ground": "🌎",
            "flying": "🪽",
            "psychic": "🔮",
            "bug": "🐛",
            "rock": "🪨",
            "ghost": "👻",
            "dragon": "🐉",
            "dark": "🌑",
            "steel": "⚙️",
            "fairy": "🧚",
        }.get(
            confirmation.cost.type.value,
            "🍬",
        )

        view = EvolutionConfirmView(
            core=self._core,
            trainer_id=ctx.author.id,
            collection_number=collection_number,
            rule=rule,
        )

        await ctx.send(
            (
                "## ✨ Confirm Evolution\n\n"
                f"**{confirmation.previous_species.name.title()}** "
                f"➡️ "
                f"**{confirmation.evolved_species.name.title()}**\n\n"
                f"{emoji} **{confirmation.cost.type.value.title()} Candy**\n"
                f"🍬 Cost: **{confirmation.cost.amount}**\n"
                f"🎒 You have: **{confirmation.current_candies}**\n\n"
                "Do you want to evolve this Pokémon?"
            ),
            view=view,
        )
