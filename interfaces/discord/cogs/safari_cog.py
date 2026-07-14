from __future__ import annotations

import logging
from datetime import UTC, datetime

from discord.ext import commands

from application.bootstrap.core import CoreServices
from application.safari import (
    SafariActivityAlreadyExists,
    SafariUnlockUnavailable,
)
from interfaces.discord.safari_errors import safari_error_message
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
