from __future__ import annotations

from collections import defaultdict

from discord.ext import commands

from application.bootstrap.core import CoreServices
from interfaces.discord.application_emojis import get_application_emojis
from interfaces.discord.input_normalizer import normalize_text
from interfaces.discord.views.duplicates_view import (
    DuplicatesView,
    build_duplicate_pages,
    format_duplicate_species_blocks,
)

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

    async def _send_groups(self, ctx, groups) -> None:
        emoji_index = await get_application_emojis(ctx.bot)
        blocks = [
            block
            for species, creatures in groups
            for block in format_duplicate_species_blocks(
                species,
                creatures,
                emoji_index,
            )
        ]
        view = DuplicatesView(ctx.author.id, build_duplicate_pages(blocks))
        message = await ctx.send(embed=view.build_embed(), view=view)
        view.message = message

    async def _groups_from_results(
        self,
        trainer_id,
        duplicate_results,
        pokemon_type=None,
    ):
        collection_service = getattr(self.core, "creature_collection_service", None)
        loader = getattr(collection_service, "get_top_collection", None)
        if loader is None:
            return []

        creatures = await loader(
            trainer_id=trainer_id,
            pokemon_type=pokemon_type,
        )
        grouped = defaultdict(list)
        for creature in creatures:
            grouped[creature.species.id].append(creature)

        return [
            (grouped[duplicate.species_id][0].species, grouped[duplicate.species_id])
            for duplicate in duplicate_results
            if duplicate.species_id in grouped
        ]

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
                groups = await self._groups_from_results(
                    ctx.author.id,
                    duplicates,
                    filter_value,
                )
                await self._send_groups(ctx, groups)
                return

            try:
                species_info = await self.core.species_info_service.get_species_info(
                    trainer_id=ctx.author.id,
                    species_name=filter_value,
                )
            except ValueError as error:
                await ctx.send(f"❌ {error}")
                return

            creatures = species_info.creatures
            if len(creatures) < 2:
                await ctx.send(
                    f"🎉 You don't have duplicate "
                    f"{species_info.species.name.title()}."
                )
                return
            await self._send_groups(
                ctx,
                [(species_info.species, list(creatures))],
            )
            return

        duplicates = await self.core.duplicate_application.get_duplicates(
            trainer_id=ctx.author.id,
        )
        if not duplicates:
            await ctx.send("🎉 You don't have any duplicate Pokémon.")
            return

        groups = await self._groups_from_results(ctx.author.id, duplicates)
        await self._send_groups(ctx, groups)
