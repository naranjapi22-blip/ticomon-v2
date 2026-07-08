import discord


class PokedexButton(discord.ui.Button):
    def __init__(self, core):
        super().__init__(
            label="📖 Pokédex",
            style=discord.ButtonStyle.secondary,
        )

        self._core = core

    async def callback(
        self,
        interaction: discord.Interaction,
    ):
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
            description=(f"**{species.name.title()}**\n\n" f"{status}"),
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )
