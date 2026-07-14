from __future__ import annotations

import logging
from datetime import UTC, datetime

import discord

from application.bootstrap.core import CoreServices
from application.safari import (
    SafariInsufficientParticipants,
    SafariRegistrationNotFound,
    SafariUnlockUnavailable,
    StartSafariResult,
)
from core.safari.registration import SafariRegistrationClosed
from interfaces.discord.safari_errors import safari_error_message
from interfaces.discord.safari_message import clear_active_safari_message
from interfaces.discord.safari_timing import (
    SAFARI_SELECTION_SECONDS,
    deadline_after,
)
from interfaces.discord.views.safari_encounter_view import SafariEncounterView

logger = logging.getLogger(__name__)


class SafariRegistrationView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        guild_id: int,
        registration_result,
    ) -> None:
        super().__init__(timeout=300)

        self.core = core
        self.guild_id = guild_id
        self.registration_result = registration_result
        self.message: discord.Message | None = None

    def build_content(self) -> str:
        return (
            "Safari Ready\n"
            f"A level {self.registration_result.level} Safari is available."
        )

    def build_embed(self) -> discord.Embed:
        registration = self.registration_result.registration
        participant_ids = sorted(registration.participant_ids)
        participants = (
            "\n".join(f"<@{trainer_id}>" for trainer_id in participant_ids)
            if participant_ids
            else "No participants yet."
        )

        embed = discord.Embed(
            title="🧭 Safari Registration",
            description="Join the expedition before it starts.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Level", value=str(self.registration_result.level))
        embed.add_field(
            name="Encounters",
            value=str(self.registration_result.encounter_count),
        )
        embed.add_field(
            name="Balls per participant",
            value=str(self.registration_result.balls_per_participant),
        )
        embed.add_field(
            name="Participants",
            value=participants,
            inline=False,
        )
        embed.add_field(
            name="Capacity",
            value=f"{registration.participant_count}/{self.registration_result.capacity}",
            inline=False,
        )
        return embed

    @discord.ui.button(
        label="Join Safari",
        style=discord.ButtonStyle.success,
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            await self.core.safari_registration_application.join(
                self.guild_id,
                interaction.user.id,
            )
        except SafariRegistrationNotFound:
            await interaction.response.send_message(
                safari_error_message(SafariRegistrationNotFound()),
                ephemeral=True,
            )
            return
        except SafariRegistrationClosed:
            await interaction.response.send_message(
                safari_error_message(SafariRegistrationClosed()),
                ephemeral=True,
            )
            return
        except ValueError as error:
            await interaction.response.send_message(
                safari_error_message(error),
                ephemeral=True,
            )
            return

        await interaction.response.edit_message(
            embed=self.build_embed(),
            view=self,
        )

    @discord.ui.button(
        label="Start Safari",
        style=discord.ButtonStyle.primary,
    )
    async def start_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            result: StartSafariResult = await self.core.start_safari_application.start(
                self.guild_id,
                datetime.now(UTC),
            )
        except SafariRegistrationNotFound:
            await interaction.response.send_message(
                safari_error_message(SafariRegistrationNotFound()),
                ephemeral=True,
            )
            return
        except SafariInsufficientParticipants:
            await interaction.response.send_message(
                safari_error_message(SafariInsufficientParticipants()),
                ephemeral=True,
            )
            return
        except SafariUnlockUnavailable:
            await interaction.response.send_message(
                safari_error_message(SafariUnlockUnavailable()),
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
        view = SafariEncounterView(
            core=self.core,
            guild_id=self.guild_id,
            session=result.session,
            selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
        )
        view.message = self.message
        content, file = await view.build_message()
        await interaction.response.edit_message(
            content=content,
            view=view,
            attachments=[file],
        )
        view.start_selection_timer()

    @discord.ui.button(
        label="Cancel Safari",
        style=discord.ButtonStyle.danger,
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            await self.core.safari_registration_application.cancel(self.guild_id)
        except SafariRegistrationNotFound:
            await interaction.response.send_message(
                safari_error_message(SafariRegistrationNotFound()),
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

        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.clear(self.guild_id)
        await clear_active_safari_message(self.core, self.guild_id)

        await interaction.response.edit_message(
            content="Safari registration cancelled.",
            embed=None,
            view=self,
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(
                content=(
                    "This Safari interface expired. Use !safariresume to continue."
                ),
                view=self,
            )
        await clear_active_safari_message(self.core, self.guild_id)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        logger.exception(
            "safari_registration_view_error guild_id=%s user_id=%s item=%s",
            self.guild_id,
            getattr(interaction.user, "id", None),
            getattr(item, "label", item.__class__.__name__),
            exc_info=(type(error), error, error.__traceback__),
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Safari registration failed. Please try again.",
                ephemeral=True,
            )
