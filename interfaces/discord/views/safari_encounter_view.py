from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

import discord

from application.bootstrap.core import CoreServices
from application.safari import (
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
from interfaces.discord.safari_timing import (
    SAFARI_SELECTION_SECONDS,
    SAFARI_VIEW_EXPIRED_MESSAGE,
    SAFARI_VIEW_FALLBACK_SECONDS,
    deadline_after,
    remaining_seconds,
)
from rendering.safari import SafariEncounterRenderer

logger = logging.getLogger(__name__)


class SafariEncounterSlotSelect(discord.ui.Select):
    def __init__(self, view: "SafariEncounterView") -> None:
        encounter = view.session.current_encounter
        assert encounter is not None

        options = []
        for index, slot in enumerate(encounter.slots, start=1):
            species = slot.opportunity.species
            description = [species.name.title()]
            if slot.opportunity.is_shiny:
                description.append("Shiny")
            if slot.opportunity.initial_form is not None:
                description.append(slot.opportunity.initial_form.name)
            options.append(
                discord.SelectOption(
                    label=f"Slot {index}",
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


class SafariEncounterView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        guild_id: int,
        session: SafariSession,
        selection_deadline: datetime | None = None,
    ) -> None:
        super().__init__(timeout=SAFARI_VIEW_FALLBACK_SECONDS)

        self.core = core
        self.guild_id = guild_id
        self.session = session
        self.message: discord.Message | None = None
        self.renderer = SafariEncounterRenderer()
        self._selection_deadline = selection_deadline
        self._timer_task: asyncio.Task[None] | None = None
        self._timer_lock = asyncio.Lock()
        self._timer_processed = False

        self.add_item(SafariEncounterSlotSelect(self))
        self.add_item(
            PokedexButton(
                self.core,
                species_ids=tuple(
                    slot.opportunity.species.id for slot in self._encounter().slots
                ),
            )
        )

    def build_embed(self) -> discord.Embed:
        progress = self.session.completed_encounter_count + 1

        embed = discord.Embed(
            title=f"Safari Encounter {progress}/{self.session.total_encounters}",
            description="Choose a Pokémon and the number of Safari Balls to use.",
            color=discord.Color.green(),
        )
        embed.set_image(url="attachment://safari-encounter.png")

        return embed

    async def build_file(self) -> discord.File:
        image = await asyncio.to_thread(self.renderer.render, self.session)
        return image_to_discord_file(image, "safari-encounter.png")

    def start_selection_timer(self) -> None:
        if self._selection_deadline is None:
            self._selection_deadline = deadline_after(SAFARI_SELECTION_SECONDS)

        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.clear_deadlines(self.guild_id)
            tracker.set_selection_deadline(self.guild_id, self._selection_deadline)

        self.cancel_timeout_task()
        self._timer_processed = False
        self._timer_task = asyncio.create_task(self._run_selection_timeout())
        if tracker is not None:
            tracker.set_timer_task(self.guild_id, self._timer_task)

    def cancel_timeout_task(self) -> None:
        if self._timer_task is None:
            return

        if not self._timer_task.done():
            self._timer_task.cancel()
        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.clear_timer_task(self.guild_id, self._timer_task)
        self._timer_task = None

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
            selection_result = (
                await self.core.safari_capture_application.select_capture(
                    self.guild_id,
                    interaction.user.id,
                    slot_id,
                    ball_count,
                )
            )
            result = (
                await self.core.safari_capture_application.confirm_capture_selection(
                    self.guild_id,
                    interaction.user.id,
                )
            )
        except (
            SafariSessionNotFound,
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

        await interaction.response.send_message(
            content=(
                f"Selection confirmed: "
                f"{selection_result.slot.opportunity.species.name.title()} "
                f"with {selection_result.balls_selected} Safari Balls.\n"
                f"{result.balls_available} Safari Balls remaining."
            ),
            ephemeral=True,
        )
        await self.refresh()

    async def decline_selection(self, trainer_id: int) -> None:
        await self.core.safari_capture_application.decline_capture(
            self.guild_id,
            trainer_id,
        )
        await self.refresh()

    async def refresh(self) -> None:
        if self.message is not None:
            await self.message.edit(
                embed=self.build_embed(),
                view=self,
            )

    async def expire_interface(self) -> None:
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(
                content=SAFARI_VIEW_EXPIRED_MESSAGE,
                view=self,
            )

    async def on_timeout(self) -> None:
        if self._timer_processed:
            return
        await self.expire_interface()

    async def _run_selection_timeout(self) -> None:
        try:
            await asyncio.sleep(remaining_seconds(self._selection_deadline))
            async with self._timer_lock:
                if self._timer_processed:
                    return
                self._timer_processed = True
            await self._resolve_selection_timeout()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception(
                "safari_selection_timeout_failed guild_id=%s session_id=%s",
                self.guild_id,
                self.session.id,
            )
            raise
        finally:
            tracker = getattr(self.core, "safari_activity_tracker", None)
            if tracker is not None:
                tracker.clear_timer_task(self.guild_id, self._timer_task)

    async def _resolve_selection_timeout(self) -> None:
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
            logger.warning(
                "safari_selection_timeout_skipped guild_id=%s session_id=%s error=%s",
                self.guild_id,
                self.session.id,
                type(error).__name__,
            )
            return
        except Exception:
            logger.exception(
                "safari_selection_timeout_resolution_failed guild_id=%s session_id=%s",
                self.guild_id,
                self.session.id,
            )
            return

        self.session = result.session
        self.stop()
        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.clear_timer_task(self.guild_id, self._timer_task)
        if result.next_session_status is SafariSessionStatus.ROUTE_DECISION:
            await self._show_route_vote()
            return

        if result.next_session_status is SafariSessionStatus.ENCOUNTER:
            await self._show_next_encounter(result.session)
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
        if self.message is not None:
            await self.message.edit(
                embeds=view.build_embeds(),
                view=view,
                attachments=[file],
            )

    async def _show_route_vote(self) -> None:
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
        if self.message is not None:
            await self.message.edit(
                embed=view.build_embed(),
                view=view,
                attachments=[],
            )
        view.start_route_timer()

    async def _show_next_encounter(self, session: SafariSession) -> None:
        view = SafariEncounterView(
            core=self.core,
            guild_id=self.guild_id,
            session=session,
        )
        view.message = self.message
        file = await view.build_file()
        if self.message is not None:
            await self.message.edit(
                embed=view.build_embed(),
                view=view,
                attachments=[file],
            )
        view.start_selection_timer()

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
        self.add_item(SafariBallDeclineButton(self))

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


class SafariBallDeclineButton(discord.ui.Button):
    def __init__(self, view: "SafariBallCountView") -> None:
        super().__init__(
            label="Decline",
            style=discord.ButtonStyle.danger,
            row=1,
        )
        self._selection_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            await self._selection_view.parent_view.decline_selection(
                interaction.user.id
            )
        except (
            SafariSessionNotFound,
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

        for child in self._selection_view.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="Selection declined.",
            embed=None,
            view=self._selection_view,
        )
