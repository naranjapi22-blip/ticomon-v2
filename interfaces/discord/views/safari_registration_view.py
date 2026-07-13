from __future__ import annotations

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
from interfaces.discord.views.safari_encounter_view import SafariEncounterView


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
                "Safari registration is no longer available.",
                ephemeral=True,
            )
            return
        except SafariRegistrationClosed:
            await interaction.response.send_message(
                "Safari registration is already closed.",
                ephemeral=True,
            )
            return
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
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
                "Safari registration is no longer available.",
                ephemeral=True,
            )
            return
        except SafariInsufficientParticipants:
            await interaction.response.send_message(
                "Safari requires at least two participants.",
                ephemeral=True,
            )
            return
        except SafariUnlockUnavailable:
            await interaction.response.send_message(
                "The Safari unlock is no longer available.",
                ephemeral=True,
            )
            return
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        view = SafariEncounterView(
            core=self.core,
            guild_id=self.guild_id,
            session=result.session,
        )
        view.message = self.message
        await interaction.response.edit_message(
            embed=view.build_embed(),
            view=view,
            attachments=[],
        )

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
                "Safari registration is no longer available.",
                ephemeral=True,
            )
            return
        except ValueError as error:
            await interaction.response.send_message(str(error), ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            content="Safari registration cancelled.",
            embed=None,
            view=self,
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(view=self)
