import discord

from application.bootstrap.core import CoreServices
from core.starter.starter_catalog import STARTER_SPECIES
from interfaces.discord.views.starter_select import StarterSelect


class StarterView(discord.ui.View):

    def __init__(
        self,
        core: CoreServices,
        trainer_id: int,
    ):
        super().__init__(timeout=300)

        self.core = core
        self.trainer_id = trainer_id

        self.message: discord.Message | None = None

        self.starters = ()

    async def initialize(
        self,
    ):
        self.starters = await self.core.species_repository.get_many(
            STARTER_SPECIES,
        )

        self.build_components()

    def build_components(
        self,
    ):
        self.clear_items()

        self.add_item(
            StarterSelect(
                starters=self.starters,
            )
        )

    def build_embed(
        self,
    ) -> discord.Embed:
        return discord.Embed(
            title="🌟 Choose Your Starter Pokémon",
            description=(
                "Choose the Pokémon that will accompany "
                "you throughout your adventure."
            ),
            color=discord.Color.blurple(),
        )

    async def choose_starter(
        self,
        interaction: discord.Interaction,
        species_id: int,
    ):
        await interaction.response.send_message(
            f"Starter selected: {species_id}",
            ephemeral=True,
        )

    async def refresh(
        self,
        interaction: discord.Interaction,
    ):
        self.build_components()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "❌ This isn't your starter selection.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(
        self,
    ):
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(
                view=self,
            )
