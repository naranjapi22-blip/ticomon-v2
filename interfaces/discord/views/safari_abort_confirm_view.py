from __future__ import annotations

import logging

import discord

from application.bootstrap.core import CoreServices
from application.safari import SafariActivityNotFound
from interfaces.discord.safari_errors import safari_error_message
from interfaces.discord.safari_message import delete_active_safari_message

logger = logging.getLogger(__name__)


class SafariAbortConfirmView(discord.ui.View):
    def __init__(self, core: CoreServices, guild_id: int, trainer_id: int) -> None:
        super().__init__(timeout=60)

        self.core = core
        self.guild_id = guild_id
        self.trainer_id = trainer_id
        self.message: discord.Message | None = None

    @discord.ui.button(label="Abort Safari", style=discord.ButtonStyle.danger)
    async def abort_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            await self.core.safari_abort_application.abort(
                self.guild_id,
                self.trainer_id,
            )
        except SafariActivityNotFound as error:
            await interaction.response.send_message(
                safari_error_message(error),
                ephemeral=True,
            )
            return
        except ValueError as error:
            await interaction.response.send_message(
                safari_error_message(error),
                ephemeral=True,
            )
            return

        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await delete_active_safari_message(
                self.core,
                self.guild_id,
                self.message.channel,
            )

        await interaction.response.edit_message(
            content=(
                "The active Safari was aborted. Persisted captures and rewards "
                "were not changed."
            ),
            view=self,
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="Safari abort cancelled.",
            view=self,
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(
                content="Safari abort confirmation expired.",
                view=self,
            )

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        logger.exception(
            "safari_abort_confirm_error guild_id=%s trainer_id=%s item=%s",
            self.guild_id,
            self.trainer_id,
            getattr(item, "label", item.__class__.__name__),
            exc_info=(type(error), error, error.__traceback__),
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Safari abort failed. Please try again.",
                ephemeral=True,
            )
