from __future__ import annotations

from datetime import UTC, datetime

from discord.ext import commands

from application.bootstrap.core import CoreServices
from application.safari import (
    SafariActivityAlreadyExists,
    SafariActivitySnapshot,
    SafariRegistrationNotFound,
    SafariUnlockUnavailable,
)
from application.safari.results import OpenSafariRegistrationResult
from core.safari import (
    SAFARI_UNLOCK_THRESHOLD,
    SafariRegistration,
    SafariSession,
    SafariSessionStatus,
)
from core.safari.domain import (
    SAFARI_LEVEL_CONFIGS,
    SAFARI_MAX_PARTICIPANTS,
    SafariMapInfluence,
)
from core.safari.unlock import SafariUnlock
from interfaces.discord.safari_errors import safari_error_message
from interfaces.discord.safari_timing import (
    SAFARI_SELECTION_SECONDS,
    deadline_after,
)
from interfaces.discord.views.safari_abort_confirm_view import (
    SafariAbortConfirmView,
)
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_registration_view import (
    SafariRegistrationView,
)
from interfaces.discord.views.safari_route_view import SafariRouteView
from interfaces.discord.views.safari_summary import SafariSummaryView


class SafariCog(commands.Cog):
    def __init__(self, core: CoreServices) -> None:
        self.core = core

    @commands.command(name="safari")
    async def safari(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.send("Safari can only be used in a server.")
            return

        try:
            result = await self.core.safari_registration_application.open(
                ctx.guild.id,
                ctx.author.id,
                datetime.now(UTC),
            )
        except SafariUnlockUnavailable:
            await self._show_unlock_progress(ctx)
            return
        except SafariActivityAlreadyExists:
            await ctx.send(
                "A Safari is already active.\nUse !safariresume to continue it."
            )
            return
        except ValueError as error:
            await ctx.send(f"Safari could not be opened: {safari_error_message(error)}")
            return

        await self._send_registration(ctx, result)

    @commands.command(name="safariunlock")
    async def safariunlock(self, ctx: commands.Context, level: int = 1) -> None:
        if ctx.guild is None:
            await ctx.send("Safari can only be used in a server.")
            return

        if not self._is_admin_or_owner(ctx):
            await ctx.send(
                "You must be the server owner or have administrator permissions."
            )
            return

        configuration = SAFARI_LEVEL_CONFIGS.get(level)
        if configuration is None:
            available_levels = ", ".join(
                str(item) for item in sorted(SAFARI_LEVEL_CONFIGS)
            )
            await ctx.send(
                "Invalid Safari level. Available levels: " f"{available_levels}."
            )
            return

        unlock = SafariUnlock(
            id=None,
            guild_id=ctx.guild.id,
            level=level,
            encounter_count=configuration.encounter_count,
            balls_per_participant=configuration.balls_per_participant,
            unlocked_at=datetime.now(UTC),
            map_influence=SafariMapInfluence(),
        )
        saved_unlock = await self.core.safari_unlock_repository.save(unlock)

        await ctx.send(
            (
                f"Safari level {saved_unlock.level} unlocked for this server.\n"
                f"Encounters: {saved_unlock.encounter_count}\n"
                f"Safari Balls per participant: "
                f"{saved_unlock.balls_per_participant}\n"
                f"Decisions: {configuration.decision_count}"
            )
        )

    @commands.command(name="safaritest")
    async def safaritest(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.send("Safari can only be used in a server.")
            return

        if not self._is_admin_or_owner(ctx):
            await ctx.send(
                "You must be the server owner or have administrator permissions."
            )
            return

        try:
            await self.core.safari_registration_application.open(
                ctx.guild.id,
                ctx.author.id,
                datetime.now(UTC),
            )
        except SafariActivityAlreadyExists:
            try:
                await self.core.safari_registration_application.join(
                    ctx.guild.id,
                    ctx.author.id,
                )
            except SafariRegistrationNotFound:
                await ctx.send("A Safari activity is already active for this guild.")
                return
        except SafariUnlockUnavailable:
            await ctx.send(
                "No Safari unlock is available. Use !safariunlock [level] first."
            )
            return
        except ValueError as error:
            await ctx.send(f"Safari could not be opened: {safari_error_message(error)}")
            return

        try:
            result = await self.core.start_safari_application.start_for_testing(
                ctx.guild.id,
                datetime.now(UTC),
            )
        except SafariUnlockUnavailable:
            await ctx.send(
                "No Safari unlock is available. Use !safariunlock [level] first."
            )
            return
        except SafariActivityAlreadyExists:
            await ctx.send("A Safari activity is already active for this guild.")
            return
        except ValueError as error:
            await ctx.send(f"Safari could not be opened: {safari_error_message(error)}")
            return

        await self._send_encounter(
            ctx,
            result.session,
            selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
        )

    @commands.command(name="safariresume")
    async def safariresume(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.send("Safari can only be used in a server.")
            return

        snapshot = await self.core.safari_activity_application.get(ctx.guild.id)
        if snapshot is None:
            await ctx.send("No Safari activity is available to resume.")
            return

        await self._resume_snapshot(ctx, snapshot)

    @commands.command(name="safariabort")
    async def safariabort(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.send("Safari can only be used in a server.")
            return

        if not self._is_admin_or_owner(ctx):
            await ctx.send(
                "You must be the server owner or have administrator permissions."
            )
            return

        snapshot = await self.core.safari_activity_application.get(ctx.guild.id)
        if snapshot is None:
            await ctx.send("No Safari activity is available to abort.")
            return

        view = SafariAbortConfirmView(
            self.core,
            ctx.guild.id,
            ctx.author.id,
        )
        message = await ctx.send(
            content="Confirm Safari abort?",
            view=view,
        )
        view.message = message

    async def _send_registration(
        self,
        ctx: commands.Context,
        result: OpenSafariRegistrationResult,
    ) -> None:
        view = SafariRegistrationView(
            core=self.core,
            guild_id=ctx.guild.id,
            registration_result=result,
        )
        message = await ctx.send(
            content=view.build_content(),
            embed=view.build_embed(),
            view=view,
        )
        view.message = message

    async def _send_encounter(
        self,
        ctx: commands.Context,
        session: SafariSession,
        *,
        selection_deadline: datetime | None,
    ) -> None:
        view = SafariEncounterView(
            core=self.core,
            guild_id=ctx.guild.id,
            session=session,
            selection_deadline=selection_deadline,
        )
        content, file = await view.build_message()
        message = await ctx.send(
            content=content,
            file=file,
            view=view,
        )
        view.message = message
        view.start_selection_timer()

    async def _resume_snapshot(
        self,
        ctx: commands.Context,
        snapshot: SafariActivitySnapshot,
    ) -> None:
        activity = snapshot.activity
        if isinstance(activity, SafariRegistration):
            result = await self._build_registration_result(activity)
            await self._send_registration(ctx, result)
            return

        session = activity
        if session.status is SafariSessionStatus.FINISHED:
            await self._show_summary(ctx)
            return

        if session.current_route_vote is not None:
            await self._resume_route_vote(ctx, session, snapshot)
            return

        if session.current_encounter is not None:
            await self._resume_encounter(ctx, session, snapshot)
            return

        await self._show_summary(ctx)

    async def _resume_encounter(
        self,
        ctx: commands.Context,
        session: SafariSession,
        snapshot: SafariActivitySnapshot,
    ) -> None:
        deadline = snapshot.timing.selection_deadline
        if deadline is not None and deadline <= datetime.now(UTC):
            await self._resolve_expired_encounter(ctx)
            return

        await self._send_encounter(
            ctx,
            session,
            selection_deadline=deadline,
        )

    async def _resume_route_vote(
        self,
        ctx: commands.Context,
        session: SafariSession,
        snapshot: SafariActivitySnapshot,
    ) -> None:
        deadline = snapshot.timing.route_vote_deadline
        if deadline is not None and deadline <= datetime.now(UTC):
            await self._resolve_expired_route_vote(ctx)
            return

        vote = session.current_route_vote
        assert vote is not None
        view = SafariRouteView(
            core=self.core,
            guild_id=ctx.guild.id,
            session=session,
            vote=vote,
            options=vote.options,
            route_vote_deadline=deadline,
        )
        message = await ctx.send(
            content=view.build_content(),
            view=view,
        )
        view.message = message
        view.start_route_timer()

    async def _resolve_expired_encounter(self, ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.cancel_timer(guild_id)
        await self.core.safari_capture_application.close_capture_selection(guild_id)
        result = await self.core.safari_capture_application.resolve_capture(guild_id)
        session = result.session

        if result.next_session_status is SafariSessionStatus.ROUTE_DECISION:
            route_vote = await self.core.safari_route_application.open_route_vote(
                guild_id,
                datetime.now(UTC),
            )
            view = SafariRouteView(
                core=self.core,
                guild_id=guild_id,
                session=route_vote.session,
                vote=route_vote.vote,
                options=route_vote.options,
            )
            message = await self._send_route_view(ctx, view)
            view.message = message
            view.start_route_timer()
            return

        if result.next_session_status is SafariSessionStatus.ENCOUNTER:
            view = SafariEncounterView(
                core=self.core,
                guild_id=guild_id,
                session=session,
                selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
            )
            message = await self._send_encounter_view(ctx, view)
            view.message = message
            view.start_selection_timer()
            return

        await self._show_summary(ctx)

    async def _resolve_expired_route_vote(self, ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.cancel_timer(guild_id)
        result = await self.core.safari_route_application.resolve_route_vote(guild_id)
        view = SafariEncounterView(
            core=self.core,
            guild_id=guild_id,
            session=result.session,
            selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
        )
        message = await self._send_encounter_view(ctx, view)
        view.message = message
        view.start_selection_timer()

    async def _show_summary(self, ctx: commands.Context) -> None:
        finish_result = await self.core.safari_finish_application.finish(ctx.guild.id)
        view = SafariSummaryView(finish_result)
        message = await self._send_summary_view(ctx, view)
        view.message = message

    async def _build_registration_result(
        self,
        registration: SafariRegistration,
    ) -> OpenSafariRegistrationResult:
        unlocks = await self.core.safari_unlock_repository.get_available_by_guild_id(
            registration.guild_id
        )
        unlock = next(
            (item for item in unlocks if item.id == registration.unlock_id),
            None,
        )
        if unlock is None:
            raise SafariUnlockUnavailable(
                "The Safari unlock reserved by this registration is unavailable."
            )

        configuration = SAFARI_LEVEL_CONFIGS[unlock.level]
        return OpenSafariRegistrationResult(
            registration=registration,
            unlock=unlock,
            level=unlock.level,
            encounter_count=configuration.encounter_count,
            balls_per_participant=configuration.balls_per_participant,
            capacity=SAFARI_MAX_PARTICIPANTS,
        )

    @staticmethod
    def _is_admin_or_owner(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False

        owner_id = getattr(ctx.guild, "owner_id", None)
        if owner_id is not None and ctx.author.id == owner_id:
            return True

        permissions = getattr(ctx.author, "guild_permissions", None)
        return bool(getattr(permissions, "administrator", False))

    async def _send_encounter_view(
        self,
        ctx: commands.Context,
        view: SafariEncounterView,
    ) -> object:
        return await ctx.send(
            content=view.build_content(),
            view=view,
            file=await view.build_file(),
        )

    async def _send_route_view(
        self,
        ctx: commands.Context,
        view: SafariRouteView,
    ) -> object:
        return await ctx.send(
            content=view.build_content(),
            view=view,
        )

    async def _send_summary_view(
        self,
        ctx: commands.Context,
        view: SafariSummaryView,
    ) -> object:
        return await ctx.send(
            embeds=view.build_embeds(),
            view=view,
        )

    async def _show_unlock_progress(self, ctx: commands.Context) -> None:
        world_repository = getattr(self.core, "safari_world_repository", None)
        current_progress = 0
        if world_repository is not None:
            world = await world_repository.get_by_guild_id(ctx.guild.id)
            if world is not None:
                current_progress = world.current_progress

        remaining = max(0, SAFARI_UNLOCK_THRESHOLD - current_progress)
        await ctx.send(
            (
                "Safari is not unlocked yet.\n\n"
                f"Safari progress: {current_progress} / {SAFARI_UNLOCK_THRESHOLD}\n"
                f"{remaining} progress points remaining."
            )
        )
