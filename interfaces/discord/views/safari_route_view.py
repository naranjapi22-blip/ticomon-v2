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
from interfaces.discord.safari_errors import safari_error_message
from interfaces.discord.safari_timing import (
    SAFARI_ROUTE_VOTE_SECONDS,
    SAFARI_VIEW_EXPIRED_MESSAGE,
    SAFARI_VIEW_FALLBACK_SECONDS,
    deadline_after,
    remaining_seconds,
)
from interfaces.discord.views.safari_encounter_view import SafariEncounterView

logger = logging.getLogger(__name__)


class SafariRouteOptionSelect(discord.ui.Select):
    def __init__(self, view: "SafariRouteView") -> None:
        options = []
        for option in view.options:
            destination = option.destination_zone.value.replace("_", " ").title()
            movement = "Stay at" if option.stays_in_same_zone else "Advance to"
            options.append(
                discord.SelectOption(
                    label=f"{movement} {destination}",
                    value=option.id,
                )
            )

        super().__init__(
            placeholder="Vote for the next route...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.cast_vote(interaction, self.values[0])


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

        self.add_item(SafariRouteOptionSelect(self))

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Safari Route Vote",
            description="Vote for the next route.",
            color=discord.Color.blurple(),
        )
        return embed

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

    async def _run_route_timeout(self) -> None:
        try:
            await asyncio.sleep(remaining_seconds(self._route_vote_deadline))
            async with self._timer_lock:
                if self._timer_processed:
                    return
                self._timer_processed = True
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
        for child in self.children:
            child.disabled = True

        view = SafariEncounterView(
            core=self.core,
            guild_id=self.guild_id,
            session=result.session,
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
