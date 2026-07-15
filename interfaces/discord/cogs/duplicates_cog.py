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

    def __init__(
        self,
        core: CoreServices,
    ):
        self.core = core

    @commands.command(
        name="duplicates",
    )
    async def duplicates(
        self,
        ctx: commands.Context,
        *,
        filtro: str | None = None,
    ):

        if filtro:
            filtro = normalize_text(filtro)

            if filtro in POKEMON_TYPES:

                duplicates = (
                    await self.core.duplicate_application.get_duplicates_by_type(
                        trainer_id=ctx.author.id,
                        pokemon_type=filtro,
                    )
                )

                if not duplicates:
                    await ctx.send(
                        (f"🎉 You don't have duplicate " f"{filtro.title()} Pokémon.")
                    )
                    return

                lines = "\n".join(
                    (f"• {duplicate.species_name.title()} " f"×{duplicate.amount}")
                    for duplicate in duplicates
                )

                await ctx.send((f"## 📦 {filtro.title()} Duplicates\n\n" f"{lines}"))

                return

            try:
                species_info = await self.core.species_info_service.get_species_info(
                    trainer_id=ctx.author.id,
                    species_name=filtro,
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
                    (
                        f"🎉 You don't have duplicate "
                        f"{species_info.species.name.title()}."
                    )
                )
                return

            lines = "\n".join(
                (f"• #{creature.collection_number} " f"{creature.iv_percentage}%")
                for creature in creatures
            )

            await ctx.send(
                (
                    f"## 📦 {species_info.species.name.title()} "
                    f"×{len(creatures)}\n\n"
                    f"{lines}"
                )
            )

            return

        duplicates = await self.core.duplicate_application.get_duplicates(
            trainer_id=ctx.author.id,
        )

        if not duplicates:
            await ctx.send("🎉 You don't have any duplicate Pokémon.")
            return

        lines = "\n".join(
            (f"• {duplicate.species_name.title()} " f"×{duplicate.amount}")
            for duplicate in duplicates
        )

        await ctx.send(("## 📦 Duplicates\n\n" f"{lines}"))
