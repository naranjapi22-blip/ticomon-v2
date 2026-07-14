from __future__ import annotations

import logging
from datetime import UTC, datetime

from discord.ext import commands

from application.bootstrap.core import CoreServices
from application.safari import (
    SafariActivityAlreadyExists,
    SafariRegistrationNotFound,
    SafariUnlockUnavailable,
)
from core.safari.domain import SAFARI_LEVEL_CONFIGS, SafariMapInfluence
from core.safari.unlock import SafariUnlock
from interfaces.discord.safari_errors import safari_error_message
from interfaces.discord.views.safari_encounter_view import SafariEncounterView
from interfaces.discord.views.safari_registration_view import (
    SafariRegistrationView,
)

logger = logging.getLogger(__name__)


class SafariCog(commands.Cog):
    def __init__(self, core: CoreServices) -> None:
        self.core = core

    @commands.command(name="safari")
    async def safari(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.send("Safari can only be used in a server.")
            return

        logger.debug(
            "safari_command_invoked guild_id=%s trainer_id=%s",
            ctx.guild.id,
            ctx.author.id,
        )
        try:
            result = await self.core.safari_registration_application.open(
                ctx.guild.id,
                ctx.author.id,
                datetime.now(UTC),
            )
        except SafariUnlockUnavailable:
            await ctx.send("No Safari unlock is available for this guild.")
            return
        except SafariActivityAlreadyExists:
            await ctx.send("A Safari activity is already active for this guild.")
            return
        except ValueError as error:
            await ctx.send(f"Safari could not be opened: {safari_error_message(error)}")
            return

        view = SafariRegistrationView(
            core=self.core,
            guild_id=ctx.guild.id,
            registration_result=result,
        )

        message = await ctx.send(
            embed=view.build_embed(),
            view=view,
        )
        view.message = message

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

        logger.debug(
            "safari_test_command_invoked guild_id=%s trainer_id=%s",
            ctx.guild.id,
            ctx.author.id,
        )

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

        view = SafariEncounterView(
            core=self.core,
            guild_id=ctx.guild.id,
            session=result.session,
        )
        message = await ctx.send(
            embed=view.build_embed(),
            view=view,
        )
        view.message = message

    @staticmethod
    def _is_admin_or_owner(ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False

        owner_id = getattr(ctx.guild, "owner_id", None)
        if owner_id is not None and ctx.author.id == owner_id:
            return True

        permissions = getattr(ctx.author, "guild_permissions", None)
        return bool(getattr(permissions, "administrator", False))
