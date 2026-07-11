import discord

from application.adventure.start_adventure.exceptions import (
    TrainerAlreadyExistsError,
)
from application.bootstrap.core import CoreServices
from core.starter.starter_catalog import STARTER_REGIONS
from interfaces.discord.views.back_button import BackButton
from interfaces.discord.views.cancel_button import CancelButton
from interfaces.discord.views.change_starter_button import (
    ChangeStarterButton,
)
from interfaces.discord.views.confirm_button import ConfirmButton
from interfaces.discord.views.region_select import RegionSelect
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

        self.selected_region: str | None = None
        self.pending_species_id: int | None = None
        self.starters = ()

    async def initialize(
        self,
    ):
        self.build_components()

    def build_components(
        self,
    ):
        self.clear_items()

        if self.pending_species_id is not None:
            self.add_item(
                ChangeStarterButton(),
            )

            self.add_item(
                ConfirmButton(),
            )
            return

        if self.selected_region is None:
            self.add_item(
                RegionSelect(),
            )
            return

        self.add_item(
            StarterSelect(
                starters=self.starters,
            )
        )

        self.add_item(
            BackButton(),
        )

        self.add_item(
            CancelButton(),
        )

    async def choose_region(
        self,
        interaction: discord.Interaction,
        region: str,
    ):
        self.selected_region = region

        species_ids = STARTER_REGIONS[region]

        self.starters = await self.core.species_repository.get_many(
            species_ids,
        )

        self.build_components()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    async def select_starter(
        self,
        interaction: discord.Interaction,
        species_id: int,
    ):
        self.pending_species_id = species_id

        self.build_components()

        await interaction.response.edit_message(
            embed=self.build_confirm_embed(),
            view=self,
        )

    async def change_starter(
        self,
        interaction: discord.Interaction,
    ):
        self.pending_species_id = None

        self.build_components()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    async def go_back(
        self,
        interaction: discord.Interaction,
    ):
        self.selected_region = None
        self.pending_species_id = None
        self.starters = ()

        self.build_components()

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    def build_embed(
        self,
    ) -> discord.Embed:
        if self.selected_region is None:
            return discord.Embed(
                title="🌍 Choose Your Region",
                description=("Choose the region where your adventure begins."),
                color=discord.Color.blurple(),
            )

        return discord.Embed(
            title=f"🌟 {self.selected_region} Starters",
            description=(
                "Choose the Pokémon that will accompany "
                "you throughout your adventure."
            ),
            color=discord.Color.blurple(),
        )

    def build_confirm_embed(
        self,
    ) -> discord.Embed:

        species = next(
            starter
            for starter in self.starters
            if starter.id == self.pending_species_id
        )

        return discord.Embed(
            title="⚠️ Confirm Your Starter",
            description=(
                f"You selected **{species.name}**.\n\n"
                "This choice cannot be changed.\n\n"
                "Press **Begin Adventure** to start your journey."
            ),
            color=discord.Color.gold(),
        )

    async def confirm_starter(
        self,
        interaction: discord.Interaction,
    ):
        await self.choose_starter(
            interaction,
            self.pending_species_id,
        )

    async def choose_starter(
        self,
        interaction: discord.Interaction,
        species_id: int,
    ):
        try:
            result = await self.core.start_adventure_application.start(
                trainer_id=self.trainer_id,
                starter_species_id=species_id,
            )
        except TrainerAlreadyExistsError:
            await interaction.response.send_message(
                "You have already started your adventure.",
                ephemeral=True,
            )
            return

        self.pending_species_id = None

        for child in self.children:
            child.disabled = True

        embed = discord.Embed(
            title="🎉 Adventure Started!",
            description=(
                f"You chose **{result.starter.species.name}** "
                "as your first partner.\n\n"
                "Your adventure begins now!"
            ),
            color=discord.Color.green(),
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )

    async def cancel(
        self,
        interaction: discord.Interaction,
    ):
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content=(
                "Starter selection cancelled.\n"
                "Use **!spawn** when you're ready to begin."
            ),
            embed=None,
            view=self,
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
