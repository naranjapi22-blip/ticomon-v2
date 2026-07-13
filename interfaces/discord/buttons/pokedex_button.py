from __future__ import annotations

from collections.abc import Sequence

import discord


class PokedexButton(discord.ui.Button):
    def __init__(
        self,
        core,
        species_ids: Sequence[int] | None = None,
    ) -> None:
        super().__init__(
            label="📖 Pokédex",
            style=discord.ButtonStyle.secondary,
        )

        self._core = core
        self._species_ids = tuple(species_ids) if species_ids is not None else None

    async def callback(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if self._species_ids is None:
            await self._show_spawn_pokedex(interaction)
            return

        await self._show_safari_pokedex(interaction)

    async def _show_spawn_pokedex(self, interaction: discord.Interaction) -> None:
        session = await self._core.get_current_spawn_application.get_current(
            guild_id=interaction.guild.id,
        )

        if session is None or session.selected_opportunity is None:
            await interaction.response.send_message(
                "No active Pokémon.",
                ephemeral=True,
            )
            return

        species = session.selected_opportunity.species
        registered = await self._core.creature_repository.has_species(
            trainer_id=interaction.user.id,
            species_id=species.id,
        )

        status = "✅ Registered" if registered else "❌ Not Registered"
        embed = discord.Embed(
            title="📖 Pokédex",
            description=f"**{species.name.title()}**\n\n{status}",
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    async def _show_safari_pokedex(self, interaction: discord.Interaction) -> None:
        species = await self._core.species_repository.get_many(self._species_ids)
        lines = []
        for item in species:
            caught = await self._core.creature_repository.has_species(
                trainer_id=interaction.user.id,
                species_id=item.id,
            )
            status = "✅ Caught" if caught else "❌ Missing"
            lines.append(f"**{item.name.title()}** — {status}")

        embed = discord.Embed(
            title="📖 Safari Pokédex",
            description="\n".join(lines) if lines else "No species are shown.",
            color=discord.Color.blurple(),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
