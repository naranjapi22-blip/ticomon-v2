from __future__ import annotations

from datetime import UTC, datetime

from discord.ext import commands

from application.bootstrap.core import CoreServices
from application.safari import (
    SafariActivityAlreadyExists,
    SafariActivitySnapshot,
    SafariRegistrationNotFound,
    SafariRegistrationStillOpen,
    SafariUnlockAlreadyExists,
    SafariUnlockUnavailable,
)
from application.safari.results import OpenSafariRegistrationResult
from core.safari import (
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
from interfaces.discord.safari_message import (
    delete_active_safari_message,
    remember_active_safari_message,
)
from interfaces.discord.safari_timing import (
    SAFARI_SELECTION_SECONDS,
    deadline_after,
)
from interfaces.discord.views.safari_abort_confirm_view import (
    SafariAbortConfirmView,
)
from interfaces.discord.views.safari_encounter_view import (
    publish_current_encounter,
    publish_current_route_vote,
    publish_final_summary,
)
from interfaces.discord.views.safari_registration_view import (
    SafariRegistrationView,
)


class SafariCog(commands.Cog):
    def __init__(self, core: CoreServices) -> None:
        self.core = core

    @commands.command(name="safari")
    async def safari(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.send("Safari can only be used in a server.")
            return

        activity_application = getattr(self.core, "safari_activity_application", None)
        snapshot = (
            await activity_application.get(ctx.guild.id)
            if activity_application is not None
            else None
        )
        if snapshot is not None:
            activity = snapshot.activity
            if isinstance(activity, SafariRegistration):
                try:
                    result = await self.core.start_safari_application.start(
                        ctx.guild.id,
                        datetime.now(UTC),
                    )
                except SafariRegistrationStillOpen as error:
                    await ctx.send(safari_error_message(error))
                    return
                except SafariRegistrationNotFound:
                    await ctx.send("No Safari activity is available to resume.")
                    return
                except SafariUnlockUnavailable:
                    await ctx.send(
                        "No Safari unlock is available. "
                        "Use !safariunlock [level] first."
                    )
                    return
                except ValueError as error:
                    await ctx.send(
                        f"Safari could not be opened: {safari_error_message(error)}"
                    )
                    return

                await self._send_encounter(
                    ctx,
                    result.session,
                    selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
                )
                return

            if isinstance(activity, SafariSession):
                await ctx.send(
                    "A Safari is already active.\nUse !safariresume to continue it."
                )
                return

        try:
            result = await self.core.safari_registration_application.open(
                ctx.guild.id,
                ctx.author.id,
                datetime.now(UTC),
            )
        except SafariUnlockUnavailable:
            await self._show_daily_progress(ctx)
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
        try:
            saved_unlock = await self.core.safari_unlock_repository.save(unlock)
        except SafariUnlockAlreadyExists:
            await ctx.send(f"A Safari unlock for level {level} already exists today.")
            return

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
        await delete_active_safari_message(self.core, ctx.guild.id, ctx.channel)
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
        await remember_active_safari_message(self.core, ctx.guild.id, message)

    async def _send_encounter(
        self,
        ctx: commands.Context,
        session: SafariSession,
        *,
        selection_deadline: datetime | None,
    ) -> None:
        await publish_current_encounter(
            self.core,
            ctx.guild.id,
            session,
            ctx,
            selection_deadline=selection_deadline,
        )

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
        await publish_current_route_vote(
            self.core,
            ctx.guild.id,
            session,
            ctx,
            vote=vote,
            options=vote.options,
            route_vote_deadline=deadline,
        )

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
            await publish_current_route_vote(
                self.core,
                guild_id,
                route_vote.session,
                ctx,
                vote=route_vote.vote,
                options=route_vote.options,
            )
            return

        if result.next_session_status is SafariSessionStatus.ENCOUNTER:
            await publish_current_encounter(
                self.core,
                guild_id,
                session,
                ctx,
                selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
            )
            return

        await self._show_summary(ctx)

    async def _resolve_expired_route_vote(self, ctx: commands.Context) -> None:
        guild_id = ctx.guild.id
        tracker = getattr(self.core, "safari_activity_tracker", None)
        if tracker is not None:
            tracker.cancel_timer(guild_id)
        result = await self.core.safari_route_application.resolve_route_vote(guild_id)
        await publish_current_encounter(
            self.core,
            guild_id,
            result.session,
            ctx,
            selection_deadline=deadline_after(SAFARI_SELECTION_SECONDS),
        )

    async def _show_summary(self, ctx: commands.Context) -> None:
        await publish_final_summary(
            self.core,
            ctx.guild.id,
            ctx,
        )

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

    async def _show_daily_progress(self, ctx: commands.Context) -> None:
        progress_application = getattr(
            self.core,
            "safari_daily_progress_application",
            None,
        )
        if progress_application is None:
            await ctx.send("Safari progress is unavailable right now.")
            return

        snapshot = await progress_application.get(ctx.guild.id)
        await ctx.send(
            (
                "Daily Safari Progress\n\n"
                f"Active trainers: {snapshot.active_player_count}\n"
                f"Captures today: {snapshot.daily_capture_count} / "
                f"{snapshot.daily_capture_target}\n"
                f"Safaris unlocked: {snapshot.daily_unlock_count} / 5\n"
                f"Next Safari: {snapshot.captures_remaining} captures remaining."
            )
        )
