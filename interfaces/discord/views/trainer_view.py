import math

import discord

from application.bootstrap.core import CoreServices
from application.trainer.trainer_catalog import (
    PAGE_SIZE,
    get_page,
    list_trainers,
)
from interfaces.discord.files import image_to_discord_file
from interfaces.discord.views.next_button import NextButton
from interfaces.discord.views.previous_button import PreviousButton
from interfaces.discord.views.trainer_select import TrainerSelect
from rendering.trainers.renderer import TrainerRenderer


class TrainerView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        trainer_id: int,
    ):
        super().__init__(timeout=300)

        self.core = core
        self.trainer_id = trainer_id

        self.page = 0
        self.profile = None

        self.renderer = TrainerRenderer()

        self.total_pages = math.ceil(len(list_trainers()) / PAGE_SIZE)

        self.message: discord.Message | None = None

    async def initialize(self):
        self.profile = await self.core.profile_service.get_profile(
            self.trainer_id,
        )

        self.build_components()

    def build_components(self):
        self.clear_items()

        self.add_item(
            TrainerSelect(
                trainers=get_page(self.page),
            )
        )

        self.add_item(
            PreviousButton(),
        )

        self.add_item(
            NextButton(),
        )

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="👤 Choose Your Trainer",
            description=(
                f"Current Trainer: **{self.profile.trainer.name}**\n\n"
                f"Page {self.page + 1}/{self.total_pages}"
            ),
            color=discord.Color.blurple(),
        )

        embed.set_image(
            url="attachment://trainers.png",
        )

        return embed

    def build_file(self) -> discord.File:
        image = self.renderer.render(
            trainers=get_page(self.page),
            selected=self.profile.trainer,
            page=self.page + 1,
        )

        return image_to_discord_file(
            image,
            "trainers.png",
        )

    async def refresh(
        self,
        interaction: discord.Interaction,
    ):
        self.profile = await self.core.profile_service.get_profile(
            self.trainer_id,
        )

        self.build_components()

        embed = self.build_embed()

        file = self.build_file()

        await interaction.response.edit_message(
            embed=embed,
            attachments=[file],
            view=self,
        )

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "❌ This isn't your trainer profile.",
                ephemeral=True,
            )
            return False

        return True

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(view=self)
