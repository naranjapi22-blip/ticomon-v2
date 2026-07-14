from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

import discord

from application.bootstrap.core import CoreServices
from application.safari import (
    ConfirmSafariCaptureSelectionResult,
    DeclineSafariCaptureResult,
    FinishSafariResult,
    SafariCaptureResolutionUnavailable,
    SafariCaptureSelectionNotFound,
    SafariCaptureSelectionUnavailable,
    SafariSessionNotFound,
)
from core.safari import SafariEncounter, SafariSession, SafariSessionStatus
from interfaces.discord.buttons.pokedex_button import PokedexButton
from interfaces.discord.files import image_to_discord_file
from interfaces.discord.safari_errors import safari_error_message
from rendering.safari import SafariEncounterRenderer
from rendering.safari.narrative import encounter_narrative

logger = logging.getLogger(__name__)


class SafariEncounterSlotSelect(discord.ui.Select):
    def __init__(self, view: "SafariEncounterView") -> None:
        encounter = view.session.current_encounter
        assert encounter is not None

        options = []
        for index, slot in enumerate(encounter.slots, start=1):
            species = slot.opportunity.species
            label = f"Slot {index}: {species.name.title()}"
            description = []
            if slot.opportunity.is_shiny:
                description.append("Shiny")
            if slot.opportunity.initial_form is not None:
                description.append(slot.opportunity.initial_form.name)
            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(slot.id),
                    description=", ".join(description) if description else None,
                )
            )

        super().__init__(
            placeholder="Choose a Safari slot...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        slot_id = UUID(self.values[0])
        await self.view.choose_slot(interaction, slot_id)


class SafariEncounterResolveButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(
            label="Resolve Encounter",
            style=discord.ButtonStyle.primary,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.resolve_encounter(interaction)


class SafariEncounterView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        guild_id: int,
        session: SafariSession,
    ) -> None:
        super().__init__(timeout=300)

        self.core = core
        self.guild_id = guild_id
        self.session = session
        self.message: discord.Message | None = None
        self.renderer = SafariEncounterRenderer()

        self.add_item(SafariEncounterSlotSelect(self))
        self.add_item(
            PokedexButton(
                self.core,
                species_ids=tuple(
                    slot.opportunity.species.id for slot in self._encounter().slots
                ),
            )
        )
        self.add_item(SafariEncounterResolveButton())

    def build_embed(self) -> discord.Embed:
        encounter = self._encounter()
        current_segment = self.session.current_segment
        confirmed = sum(
            1
            for selection in encounter.selections_by_trainer.values()
            if selection.is_confirmed
        )
        declined = len(encounter.declined_participant_ids)
        progress = self.session.completed_encounter_count + 1

        embed = discord.Embed(
            title=f"Safari Encounter {progress}/{self.session.total_encounters}",
            description=encounter_narrative(
                self.session.safari_map,
                self.session.weather,
                self.session.time_of_day,
                self.session.phase,
            ),
            color=discord.Color.green(),
        )
        embed.add_field(name="Map", value=self.session.safari_map.value, inline=True)
        embed.add_field(name="Zone", value=current_segment.zone.value, inline=True)
        embed.add_field(name="Weather", value=self.session.weather.value, inline=True)
        embed.add_field(name="Time", value=self.session.time_of_day.value, inline=True)
        embed.add_field(name="Phase", value=self.session.phase.value, inline=True)
        embed.add_field(
            name="Segment",
            value=f"{current_segment.remaining_encounters} encounter(s) left",
            inline=True,
        )
        embed.add_field(
            name="Decisions",
            value=(
                f"Confirmed: {confirmed}\n"
                f"Declined: {declined}\n"
                f"Eligible: {len(encounter.eligible_participant_ids)}"
            ),
            inline=False,
        )

        for index, slot in enumerate(encounter.slots, start=1):
            species = slot.opportunity.species
            details = [f"Species: {species.name.title()}"]
            if slot.opportunity.is_shiny:
                details.append("Shiny: Yes")
            if slot.opportunity.initial_form is not None:
                details.append(f"Form: {slot.opportunity.initial_form.name}")
            embed.add_field(
                name=f"Slot {index}",
                value="\n".join(details),
                inline=False,
            )

        return embed

    async def build_file(self) -> discord.File:
        image = await asyncio.to_thread(self.renderer.render, self.session)
        return image_to_discord_file(image, "safari-encounter.png")

    async def choose_slot(
        self,
        interaction: discord.Interaction,
        slot_id: UUID,
    ) -> None:
        encounter = self._encounter()
        slot = next((item for item in encounter.slots if item.id == slot_id), None)
        if slot is None:
            await interaction.response.send_message(
                "Safari slot was not found.",
                ephemeral=True,
            )
            return

        participant = self.session.participants_by_trainer.get(interaction.user.id)
        remaining_balls = participant.remaining_balls if participant is not None else 3
        if remaining_balls <= 0:
            await interaction.response.send_message(
                "You do not have any Safari Balls remaining.",
                ephemeral=True,
            )
            return

        view = SafariBallCountView(
            core=self.core,
            parent_view=self,
            trainer_id=interaction.user.id,
            slot_id=slot_id,
            slot_name=slot.opportunity.species.name.title(),
            remaining_balls=min(3, remaining_balls),
        )
        await interaction.response.send_message(
            embed=view.build_embed(),
            view=view,
            ephemeral=True,
        )

    async def select_balls(
        self,
        interaction: discord.Interaction,
        slot_id: UUID,
        ball_count: int,
    ) -> None:
        try:
            result = await self.core.safari_capture_application.select_capture(
                self.guild_id,
                interaction.user.id,
                slot_id,
                ball_count,
            )
        except (SafariSessionNotFound, SafariCaptureSelectionUnavailable) as error:
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

        confirmation = SafariCaptureConfirmationView(
            core=self.core,
            parent_view=self,
            selection_result=result,
        )
        await interaction.response.send_message(
            embed=confirmation.build_embed(),
            view=confirmation,
            ephemeral=True,
        )
        await self.refresh()

    async def confirm_selection(
        self,
        trainer_id: int,
    ) -> ConfirmSafariCaptureSelectionResult:
        try:
            result = (
                await self.core.safari_capture_application.confirm_capture_selection(
                    self.guild_id,
                    trainer_id,
                )
            )
        except (
            SafariCaptureSelectionNotFound,
            SafariCaptureSelectionUnavailable,
        ) as error:
            raise error
        except ValueError as error:
            raise error

        await self.refresh()
        return result

    async def decline_selection(
        self,
        trainer_id: int,
    ) -> DeclineSafariCaptureResult:
        try:
            result: DeclineSafariCaptureResult = (
                await self.core.safari_capture_application.decline_capture(
                    self.guild_id,
                    trainer_id,
                )
            )
        except (SafariSessionNotFound, SafariCaptureSelectionUnavailable) as error:
            raise error
        except ValueError as error:
            raise error

        await self.refresh()
        return result

    async def resolve_encounter(self, interaction: discord.Interaction) -> None:
        try:
            await self.core.safari_capture_application.close_capture_selection(
                self.guild_id,
            )
            result = await self.core.safari_capture_application.resolve_capture(
                self.guild_id,
            )
        except (
            SafariCaptureResolutionUnavailable,
            SafariCaptureSelectionUnavailable,
            SafariSessionNotFound,
        ) as error:
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

        self.session = result.session
        if result.next_session_status is SafariSessionStatus.ROUTE_DECISION:
            for child in self.children:
                child.disabled = True
            from interfaces.discord.views.safari_route_view import SafariRouteView

            route_vote = await self.core.safari_route_application.open_route_vote(
                self.guild_id,
                datetime.now(UTC),
            )
            view = SafariRouteView(
                core=self.core,
                guild_id=self.guild_id,
                session=route_vote.session,
                vote=route_vote.vote,
                options=route_vote.options,
            )
            view.message = self.message
            await interaction.response.edit_message(
                embed=view.build_embed(),
                view=view,
                attachments=[],
            )
            return

        if result.next_session_status is SafariSessionStatus.ENCOUNTER:
            for child in self.children:
                child.disabled = True
            view = SafariEncounterView(
                core=self.core,
                guild_id=self.guild_id,
                session=result.session,
            )
            view.message = self.message
            file = await view.build_file()
            await interaction.response.edit_message(
                embed=view.build_embed(),
                view=view,
                attachments=[file],
            )
            return

        from interfaces.discord.views.safari_summary import SafariSummaryView

        finish_result: FinishSafariResult = (
            await self.core.safari_finish_application.finish(
                self.guild_id,
            )
        )
        view = SafariSummaryView(
            finish_result,
        )
        view.message = self.message
        file = await view.build_file()
        await interaction.response.edit_message(
            embeds=view.build_embeds(),
            view=view,
            attachments=[file],
        )

    async def refresh(self) -> None:
        if self.message is not None:
            await self.message.edit(
                embed=self.build_embed(),
                view=self,
            )

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(view=self)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        logger.exception(
            "safari_encounter_view_error guild_id=%s user_id=%s item=%s",
            self.guild_id,
            getattr(interaction.user, "id", None),
            getattr(item, "label", item.__class__.__name__),
            exc_info=(type(error), error, error.__traceback__),
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Safari encounter interaction failed. Please try again.",
                ephemeral=True,
            )

    def _encounter(self) -> SafariEncounter:
        encounter = self.session.current_encounter
        if encounter is None:
            raise SafariSessionNotFound("Safari encounter was not found.")
        return encounter


class SafariBallCountButton(discord.ui.Button):
    def __init__(self, count: int, view: "SafariBallCountView") -> None:
        super().__init__(
            label=f"{count} Ball{'s' if count > 1 else ''}",
            style=discord.ButtonStyle.secondary,
            row=0,
        )
        self._count = count
        self._selection_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._selection_view.choose_balls(
            interaction,
            self._count,
        )


class SafariBallCountView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        parent_view: SafariEncounterView,
        trainer_id: int,
        slot_id: UUID,
        slot_name: str,
        remaining_balls: int,
    ) -> None:
        super().__init__(timeout=120)

        self.core = core
        self.parent_view = parent_view
        self.trainer_id = trainer_id
        self.slot_id = slot_id
        self.slot_name = slot_name
        self.remaining_balls = remaining_balls
        self.message: discord.Message | None = None

        for count in range(1, remaining_balls + 1):
            self.add_item(SafariBallCountButton(count, self))

    def build_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Choose Safari Balls",
            description=(
                f"Selected slot: **{self.slot_name}**\n"
                f"Available Balls: {self.remaining_balls}"
            ),
            color=discord.Color.blurple(),
        )

    async def choose_balls(
        self,
        interaction: discord.Interaction,
        ball_count: int,
    ) -> None:
        await self.parent_view.select_balls(
            interaction,
            self.slot_id,
            ball_count,
        )


class SafariCaptureConfirmationView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        parent_view: SafariEncounterView,
        selection_result: ConfirmSafariCaptureSelectionResult | None = None,
    ) -> None:
        super().__init__(timeout=120)

        self.core = core
        self.parent_view = parent_view
        self.selection_result = selection_result
        self.message: discord.Message | None = None

    def build_embed(self) -> discord.Embed:
        if self.selection_result is None:
            return discord.Embed(
                title="Safari Selection",
                description="No pending selection.",
                color=discord.Color.blurple(),
            )

        selection = self.selection_result.selection
        return discord.Embed(
            title="Safari Selection Pending",
            description=(
                f"Slot: **{selection.slot_id}**\n"
                f"Balls: **{selection.ball_count}**\n"
                f"Remaining Balls: **{self.selection_result.balls_available}**"
            ),
            color=discord.Color.gold(),
        )

    @discord.ui.button(
        label="Confirm",
        style=discord.ButtonStyle.success,
    )
    async def confirm_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.selection_result is None:
            await interaction.response.send_message(
                "No pending Safari selection.",
                ephemeral=True,
            )
            return

        try:
            result = await self.parent_view.confirm_selection(interaction.user.id)
        except (
            SafariCaptureSelectionNotFound,
            SafariCaptureSelectionUnavailable,
        ) as error:
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
        await interaction.response.edit_message(
            content=(
                f"Selection confirmed. Remaining Balls: " f"{result.balls_available}."
            ),
            embed=None,
            view=self,
        )

    @discord.ui.button(
        label="Change",
        style=discord.ButtonStyle.secondary,
    )
    async def change_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await interaction.response.send_message(
            "Choose another slot or ball count in the encounter message.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Decline",
        style=discord.ButtonStyle.danger,
    )
    async def decline_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        try:
            await self.parent_view.decline_selection(interaction.user.id)
        except (SafariSessionNotFound, SafariCaptureSelectionUnavailable) as error:
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
        await interaction.response.edit_message(
            content="Selection declined.",
            embed=None,
            view=self,
        )
