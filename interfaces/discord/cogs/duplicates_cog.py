from discord.ext import commands

from application.bootstrap.core import CoreServices
from interfaces.discord.input_normalizer import normalize_text

POKEMON_TYPES = {
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
}


class DuplicatesCog(commands.Cog):
    def __init__(self, core: CoreServices):
        self.core = core

    @commands.command(name="duplicates")
    async def duplicates(
        self,
        ctx: commands.Context,
        *,
        filter_value: str | None = None,
    ):
        if filter_value:
            filter_value = normalize_text(filter_value)

            if filter_value in POKEMON_TYPES:
                duplicates = (
                    await self.core.duplicate_application.get_duplicates_by_type(
                        trainer_id=ctx.author.id,
                        pokemon_type=filter_value,
                    )
                )

                if not duplicates:
                    await ctx.send(
                        f"🎉 You don't have duplicate {filter_value.title()} Pokémon."
                    )
                    return

                lines = "\n".join(
                    f"• {duplicate.species_name.title()} ×{duplicate.amount}"
                    for duplicate in duplicates
                )

                await ctx.send(f"## 📦 {filter_value.title()} Duplicates\n\n{lines}")
                return

            try:
                species_info = await self.core.species_info_service.get_species_info(
                    trainer_id=ctx.author.id,
                    species_name=filter_value,
                )
            except ValueError as error:
                await ctx.send(f"❌ {error}")
                return

            creatures = sorted(
                species_info.creatures,
                key=lambda creature: creature.iv_percentage,
                reverse=True,
            )

            if len(creatures) < 2:
                await ctx.send(
                    f"🎉 You don't have duplicate "
                    f"{species_info.species.name.title()}."
                )
                return

            lines = "\n".join(
                f"• #{creature.collection_number} {creature.iv_percentage}%"
                for creature in creatures
            )

            await ctx.send(
                f"## 📦 {species_info.species.name.title()} "
                f"×{len(creatures)}\n\n{lines}"
            )
            return

        duplicates = await self.core.duplicate_application.get_duplicates(
            trainer_id=ctx.author.id,
        )

        if not duplicates:
            await ctx.send("🎉 You don't have any duplicate Pokémon.")
            return

        lines = "\n".join(
            f"• {duplicate.species_name.title()} ×{duplicate.amount}"
            for duplicate in duplicates
        )

        await ctx.send(f"## 📦 Duplicates\n\n{lines}")
