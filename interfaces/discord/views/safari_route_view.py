from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import discord

from application.bootstrap.core import CoreServices
from application.safari import (
    SafariRouteVoteNotFound,
    SafariRouteVoteUnavailable,
    SafariSessionNotFound,
)
from core.safari import SafariRouteOption, SafariRouteVote, SafariSession
from interfaces.discord.files import image_to_discord_file
from interfaces.discord.safari_errors import safari_error_message
from interfaces.discord.safari_timing import (
    SAFARI_PHASE_ENDED_MESSAGE,
    SAFARI_ROUTE_VOTE_SECONDS,
    SAFARI_VIEW_FALLBACK_SECONDS,
    deadline_after,
    remaining_seconds,
)
from interfaces.discord.views.safari_encounter_view import (
    publish_current_encounter,
)
from rendering.safari.assets import SafariAssets

logger = logging.getLogger(__name__)


class SafariRouteButton(discord.ui.Button):
    def __init__(
        self,
        view: "SafariRouteView",
        option: SafariRouteOption,
        row: int,
    ) -> None:
        super().__init__(
            label=view.format_option_label(option)[:80],
            style=discord.ButtonStyle.secondary,
            row=row,
        )
        self.route_option = option

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.cast_vote(interaction, self.route_option.id)


class SafariRouteView(discord.ui.View):
    def __init__(
        self,
        core: CoreServices,
        guild_id: int,
        session: SafariSession,
        vote: SafariRouteVote,
        options: tuple[SafariRouteOption, ...],
        route_vote_deadline: datetime | None = None,
    ) -> None:
        super().__init__(timeout=SAFARI_VIEW_FALLBACK_SECONDS)

        self.core = core
        self.guild_id = guild_id
        self.session = session
        self.vote = vote
        self.options = options
        self.message: discord.Message | None = None
        self._route_vote_deadline = route_vote_deadline
        self._timer_task: asyncio.Task[None] | None = None
        self._timer_lock = asyncio.Lock()
        self._timer_processed = False
        self._phase_ended = False

        for index, option in enumerate(self.options):
            self.add_item(SafariRouteButton(self, option, index // 5))

    def build_content(self) -> str:
        return (
            "Safari Route Vote\n"
            f"Vote for the next route. Resolves in {SAFARI_ROUTE_VOTE_SECONDS} seconds."
        )

    def build_file(self) -> discord.File:
        image = SafariAssets().get_background_by_name("safari.png")
        return image_to_discord_file(image, "safari.png")

    @staticmethod
    def format_option_label(option: SafariRouteOption) -> str:
        destination = option.destination_zone.value.replace("_", " ").title()
        movement = "Stay at" if option.stays_in_same_zone else "Advance to"
        return f"{movement} {destination}"

    def start_route_timer(self) -> None:
        if self._route_vote_deadline is None:
            self._route_vote_deadline = deadline_after(SAFARI_ROUTE_VOTE_SECONDS)

        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.clear_deadlines(self.guild_id)
            tracker.set_route_vote_deadline(self.guild_id, self._route_vote_deadline)

        self.cancel_timeout_task()
        self._timer_processed = False
        self._timer_task = asyncio.create_task(self._run_route_timeout())
        if tracker is not None:
            tracker.set_timer_task(self.guild_id, self._timer_task)
        logger.debug(
            "safari_route_timer_started guild_id=%s session_id=%s deadline=%s",
            self.guild_id,
            self.session.id,
            self._route_vote_deadline,
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

    async def cast_vote(
        self,
        interaction: discord.Interaction,
        option_id: str,
    ) -> None:
        if await self._reject_if_ended(interaction):
            return

        try:
            result = await self.core.safari_route_application.cast_route_vote(
                self.guild_id,
                interaction.user.id,
                option_id,
            )
        except (
            SafariSessionNotFound,
            SafariRouteVoteNotFound,
            SafariRouteVoteUnavailable,
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

        self.vote = result.vote
        await interaction.response.defer()

    async def expire_interface(self, content: str = SAFARI_PHASE_ENDED_MESSAGE) -> None:
        self._phase_ended = True
        for child in self.children:
            child.disabled = True

        if self.message is not None:
            await self.message.edit(content=content, view=self)

    async def on_timeout(self) -> None:
        if self._timer_processed:
            return
        self._timer_processed = True
        await self.expire_interface()

    async def _run_route_timeout(self) -> None:
        try:
            await asyncio.sleep(remaining_seconds(self._route_vote_deadline))
            async with self._timer_lock:
                if self._timer_processed:
                    return
                self._timer_processed = True
            await self.expire_interface()
            await self._resolve_route_timeout()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception(
                "safari_route_timeout_failed guild_id=%s session_id=%s",
                self.guild_id,
                self.session.id,
            )
            raise
        finally:
            tracker = getattr(self.core, "safari_activity_tracker", None)
            if tracker is not None:
                tracker.clear_timer_task(self.guild_id, self._timer_task)

    async def _resolve_route_timeout(self) -> None:
        try:
            result = await self.core.safari_route_application.resolve_route_vote(
                self.guild_id,
            )
        except (
            SafariSessionNotFound,
            SafariRouteVoteNotFound,
            SafariRouteVoteUnavailable,
        ) as error:
            logger.warning(
                "safari_route_timeout_skipped guild_id=%s session_id=%s error=%s",
                self.guild_id,
                self.session.id,
                type(error).__name__,
            )
            return
        except Exception:
            logger.exception(
                "safari_route_timeout_resolution_failed guild_id=%s session_id=%s",
                self.guild_id,
                self.session.id,
            )
            return

        self.session = result.session
        self.stop()
        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.clear_timer_task(self.guild_id, self._timer_task)

        logger.debug(
            "safari_next_encounter_published "
            "guild_id=%s session_id=%s encounter_id=%s encounter_index=%s",
            self.guild_id,
            self.session.id,
            (
                self.session.current_encounter.id
                if self.session.current_encounter
                else None
            ),
            self.session.completed_encounter_count + 1,
        )
        if self.message is not None:
            await publish_current_encounter(
                self.core,
                self.guild_id,
                result.session,
                self.message.channel,
                prefix_content=(
                    "Route selected: "
                    f"{self.format_option_label(result.selected_option)}"
                ),
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
