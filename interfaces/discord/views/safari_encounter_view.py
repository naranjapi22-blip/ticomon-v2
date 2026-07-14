from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
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
from core.safari import (
    SafariComposition,
    SafariEncounter,
    SafariRouteOption,
    SafariSession,
    SafariSessionStatus,
)
from interfaces.discord.buttons.pokedex_button import PokedexButton
from interfaces.discord.files import image_to_discord_file
from interfaces.discord.safari_errors import safari_error_message
from interfaces.discord.safari_message import (
    delete_active_safari_message,
    remember_active_safari_message,
)
from interfaces.discord.safari_timing import (
    SAFARI_PHASE_ENDED_MESSAGE,
    SAFARI_SELECTION_SECONDS,
    SAFARI_VIEW_FALLBACK_SECONDS,
    deadline_after,
    remaining_seconds,
)
from rendering.safari import SafariEncounterRenderer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


async def publish_current_encounter(
    core: CoreServices,
    guild_id: int,
    session: SafariSession,
    channel: discord.abc.Messageable,
    *,
    selection_deadline: datetime | None = None,
    prefix_content: str | None = None,
) -> discord.ui.View:
    await delete_active_safari_message(core, guild_id, channel)
    view = SafariEncounterView(
        core=core,
        guild_id=guild_id,
        session=session,
        selection_deadline=selection_deadline,
    )
    content, file = await view.build_message()
    if prefix_content:
        content = f"{prefix_content}\n\n{content}"
    message = await channel.send(
        content=content,
        file=file,
        view=view,
    )
    view.message = message
    await remember_active_safari_message(core, guild_id, message)
    logger.debug(
        "safari_next_encounter_published "
        "guild_id=%s session_id=%s encounter_id=%s encounter_index=%s",
        guild_id,
        session.id,
        view._encounter().id,
        session.completed_encounter_count + 1,
    )
    view.start_selection_timer()
    return view


async def publish_current_route_vote(
    core: CoreServices,
    guild_id: int,
    session: SafariSession,
    channel: discord.abc.Messageable,
    *,
    vote=None,
    options: tuple[SafariRouteOption, ...] | None = None,
    route_vote_deadline: datetime | None = None,
    prefix_content: str | None = None,
) -> discord.ui.View:
    from interfaces.discord.views.safari_route_view import SafariRouteView

    if vote is None:
        vote = session.current_route_vote
    if vote is None:
        raise SafariSessionNotFound("Safari route vote was not found.")
    if options is None:
        options = vote.options

    await delete_active_safari_message(core, guild_id, channel)
    view = SafariRouteView(
        core=core,
        guild_id=guild_id,
        session=session,
        vote=vote,
        options=options,
        route_vote_deadline=route_vote_deadline,
    )
    content = view.build_content()
    if prefix_content:
        content = f"{prefix_content}\n\n{content}"
    file = view.build_file()
    message = await channel.send(
        content=content,
        file=file,
        view=view,
    )
    view.message = message
    await remember_active_safari_message(core, guild_id, message)
    view.start_route_timer()
    return view


async def publish_final_summary(
    core: CoreServices,
    guild_id: int,
    channel: discord.abc.Messageable,
    *,
    prefix_content: str | None = None,
) -> discord.ui.View:
    from interfaces.discord.views.safari_summary import SafariSummaryView

    finish_result: FinishSafariResult = await core.safari_finish_application.finish(
        guild_id,
    )
    await delete_active_safari_message(core, guild_id, channel)
    view = SafariSummaryView(finish_result)
    kwargs = {"embeds": view.build_embeds(), "view": view}
    if prefix_content:
        kwargs["content"] = prefix_content
    message = await channel.send(**kwargs)
    view.message = message
    return view


class SafariEncounterSlotSelect(discord.ui.Select):
    def __init__(self, view: "SafariEncounterView") -> None:
        encounter = view.session.current_encounter
        assert encounter is not None

        options = []
        for index, slot in enumerate(encounter.slots, start=1):
            species = slot.opportunity.species
            description = [view.format_species_name(species.name)]
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
        self._phase_ended = False

        self.add_item(SafariEncounterSlotSelect(self))
        self.add_item(
            PokedexButton(
                self.core,
                species_ids=tuple(
                    slot.opportunity.species.id for slot in self._encounter().slots
                ),
            )
        )

    def build_content(self) -> str:
        progress = self.session.completed_encounter_count + 1
        context = " · ".join(
            (
                self.session.safari_map.value.title(),
                self.session.current_segment.zone.value.replace("_", " ").title(),
                self.session.weather.value.title(),
            )
        )
        lines = [
            f"Safari Encounter {progress}/{self.session.total_encounters}",
            context,
        ]
        special_encounter = self._special_encounter_text()
        if special_encounter is not None:
            lines.append(special_encounter)
        lines.extend(
            (
                "Choose a Pokémon and the number of Safari Balls.",
                f"Resolves in {SAFARI_SELECTION_SECONDS} seconds.",
            )
        )
        return "\n".join(lines)

    async def build_file(self) -> discord.File:
        image = await asyncio.to_thread(self.renderer.render, self.session)
        return image_to_discord_file(image, "safari-encounter.png")

    async def build_message(self) -> tuple[str, discord.File]:
        return self.build_content(), await self.build_file()

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
        logger.debug(
            "safari_selection_timer_started "
            "guild_id=%s session_id=%s encounter_id=%s encounter_index=%s "
            "deadline=%s",
            self.guild_id,
            self.session.id,
            self._encounter().id,
            self.session.completed_encounter_count + 1,
            self._selection_deadline,
        )

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
        if await self._reject_if_ended(interaction):
            return

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
            slot_name=self.format_species_name(slot.opportunity.species.name),
            remaining_balls=remaining_balls,
            selectable_balls=min(3, remaining_balls),
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
        if await self._reject_if_ended(interaction):
            return

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

        species_name = self.format_species_name(
            selection_result.slot.opportunity.species.name
        )
        selected_label = (
            "Safari Ball" if selection_result.balls_selected == 1 else "Safari Balls"
        )
        await interaction.response.send_message(
            content=(
                f"Selection confirmed: {species_name} "
                f"with {selection_result.balls_selected} {selected_label}.\n"
                f"{result.balls_available} Safari Balls remaining."
            ),
            ephemeral=True,
        )

    async def decline_selection(self, trainer_id: int) -> None:
        self._assert_not_ended()
        await self.core.safari_capture_application.decline_capture(
            self.guild_id,
            trainer_id,
        )

    async def refresh(self) -> None:
        if self.message is not None:
            await self.message.edit(
                content=self.build_content(),
                view=self,
            )

    async def expire_interface(self, content: str = SAFARI_PHASE_ENDED_MESSAGE) -> None:
        self._phase_ended = True
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(
                content=content,
                view=self,
            )

    async def on_timeout(self) -> None:
        if self._timer_processed:
            return
        self._timer_processed = True
        await self.expire_interface()

    async def _run_selection_timeout(self) -> None:
        try:
            await asyncio.sleep(remaining_seconds(self._selection_deadline))
            async with self._timer_lock:
                if self._timer_processed:
                    return
                self._timer_processed = True
            await self.expire_interface()
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
        encounter = self._encounter()
        encounter_id = encounter.id
        encounter_index = self.session.completed_encounter_count + 1
        session_id = self.session.id
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
                session_id,
                type(error).__name__,
            )
            return
        except Exception:
            logger.exception(
                "safari_selection_timeout_resolution_failed guild_id=%s session_id=%s",
                self.guild_id,
                session_id,
            )
            return

        self.session = result.session
        self.stop()
        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.clear_timer_task(self.guild_id, self._timer_task)

        logger.debug(
            "safari_encounter_transition_started "
            "guild_id=%s session_id=%s encounter_id=%s next_status=%s "
            "encounter_index=%s",
            self.guild_id,
            session_id,
            encounter_id,
            result.next_session_status.name,
            encounter_index,
        )
        results_message = self._build_encounter_results_message(result)

        if result.next_session_status is SafariSessionStatus.ROUTE_DECISION:
            await self._show_route_vote(prefix_content=results_message)
            return

        if result.next_session_status is SafariSessionStatus.ENCOUNTER:
            await self._show_next_encounter(
                result.session,
                prefix_content=results_message,
            )
            return

        await self._show_summary(prefix_content=results_message)

    async def _show_route_vote(self, *, prefix_content: str | None = None) -> None:
        if self.message is not None:
            route_vote = await self.core.safari_route_application.open_route_vote(
                self.guild_id,
                datetime.now(UTC),
            )
            await publish_current_route_vote(
                self.core,
                self.guild_id,
                route_vote.session,
                self.message.channel,
                vote=route_vote.vote,
                options=route_vote.options,
                prefix_content=prefix_content,
            )

    async def _show_next_encounter(
        self,
        session: SafariSession,
        *,
        prefix_content: str | None = None,
    ) -> None:
        if self.message is not None:
            await publish_current_encounter(
                self.core,
                self.guild_id,
                session,
                self.message.channel,
                selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
                prefix_content=prefix_content,
            )

    async def _show_summary(self, *, prefix_content: str | None = None) -> None:
        if self.message is not None:
            await publish_final_summary(
                self.core,
                self.guild_id,
                self.message.channel,
                prefix_content=prefix_content,
            )

    async def _reject_if_ended(self, interaction: discord.Interaction) -> bool:
        if not self._phase_ended:
            return False

        if not interaction.response.is_done():
            await interaction.response.send_message(
                SAFARI_PHASE_ENDED_MESSAGE,
                ephemeral=True,
            )
        return True

    def _special_encounter_text(self) -> str | None:
        encounter = self._encounter()
        labels: list[str] = []

        composition_label = self._composition_label(encounter)
        if composition_label is not None:
            labels.append(composition_label)

        event_label = self._event_label(encounter.event)
        if event_label is not None:
            labels.append(event_label)

        if not labels:
            return None
        return "Special Encounter: " + " · ".join(labels)

    @staticmethod
    def _composition_label(encounter: SafariEncounter) -> str | None:
        if encounter.composition is SafariComposition.NORMAL:
            return "Regional Herd" if encounter.is_regional_herd else None
        if encounter.composition is SafariComposition.SOLITARY:
            return "Solitary Pokémon"
        if encounter.composition is SafariComposition.DUEL:
            return "Duel"
        if encounter.composition is SafariComposition.HERD:
            return "Herd"
        if encounter.composition is SafariComposition.BABY_NEST:
            return "Baby Nest"
        if encounter.composition is SafariComposition.REGIONAL:
            return (
                "Regional Herd" if encounter.is_regional_herd else "Regional Encounter"
            )
        if encounter.composition is SafariComposition.LEGENDARY:
            return "Legendary Pokémon"
        if encounter.composition is SafariComposition.MYTHICAL:
            return "Mythical Pokémon"
        return None

    @staticmethod
    def _event_label(event) -> str | None:
        value = getattr(event, "value", "NONE")
        if value == "NONE":
            return None
        return str(value).replace("_", " ").title()

    def _assert_not_ended(self) -> None:
        if self._phase_ended:
            raise SafariSessionNotFound(SAFARI_PHASE_ENDED_MESSAGE)

    def _encounter(self) -> SafariEncounter:
        encounter = self.session.current_encounter
        if encounter is None:
            raise SafariSessionNotFound("Safari encounter was not found.")
        return encounter

    def _build_encounter_results_message(self, result) -> str:
        captured_lines: list[str] = []
        escaped_lines: list[str] = []

        for slot_result in result.slot_results:
            outcome = slot_result.slot_outcome
            if outcome.status.name == "CAPTURED" and slot_result.creature is not None:
                captured_lines.append(
                    "- "
                    f"{self.format_species_name(slot_result.creature.species.name)} "
                    f"— <@{outcome.winner_trainer_id}>"
                )
                continue

            escaped_lines.append(
                "- "
                f"{self.format_species_name(outcome.final_opportunity.species.name)}"
            )

        lines = ["Encounter Results", ""]
        if captured_lines:
            lines.append("Captured")
            lines.extend(captured_lines)
        else:
            lines.append("No Pokémon were captured.")

        if escaped_lines:
            lines.append("")
            lines.append("Escaped")
            lines.extend(escaped_lines)

        return "\n".join(lines)

    @staticmethod
    def format_species_name(name: str) -> str:
        parts = [part for part in name.replace("_", "-").split("-") if part]
        if len(parts) == 2 and len(parts[0]) > 3 and len(parts[1]) > 1:
            return f"{parts[0].title()} ({parts[1].title()})"
        return " ".join(part.title() for part in parts) or name.title()


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
        selectable_balls: int,
    ) -> None:
        super().__init__(timeout=120)

        self.core = core
        self.parent_view = parent_view
        self.trainer_id = trainer_id
        self.slot_id = slot_id
        self.slot_name = slot_name
        self.remaining_balls = remaining_balls
        self.selectable_balls = selectable_balls
        self.message: discord.Message | None = None

        for count in range(1, selectable_balls + 1):
            self.add_item(SafariBallCountButton(count, self))
        self.add_item(SafariBallDeclineButton(self))

    def build_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Choose Safari Balls",
            description=(
                f"Selected Pokémon: **{self.slot_name}**\n"
                f"Remaining Balls: {self.remaining_balls}"
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
            if await self._selection_view.parent_view._reject_if_ended(interaction):
                return
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
