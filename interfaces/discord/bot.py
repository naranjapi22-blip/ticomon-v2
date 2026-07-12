import logging
import sys

import discord
from discord.ext import commands

from interfaces.discord.bootstrap import build_discord
from interfaces.discord.cogs.candy_cog import CandyCog
from interfaces.discord.cogs.capture_cog import CaptureCog
from interfaces.discord.cogs.commands_cog import CommandsCog
from interfaces.discord.cogs.duplicates_cog import DuplicatesCog
from interfaces.discord.cogs.energy_cog import EnergyCog
from interfaces.discord.cogs.evolution_cog import EvolutionCog
from interfaces.discord.cogs.info import InfoCog
from interfaces.discord.cogs.ivs_cog import IVsCog
from interfaces.discord.cogs.pokedex_cog import PokedexCog
from interfaces.discord.cogs.profile_cog import ProfileCog
from interfaces.discord.cogs.release_cog import ReleaseCog
from interfaces.discord.cogs.select_cog import SelectCog
from interfaces.discord.cogs.spawn_cog import SpawnCog
from interfaces.discord.cogs.trade_cog import TradeCog
from interfaces.discord.cogs.trainer_cog import TrainerCog

logger = logging.getLogger(__name__)


class TicoMonBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

        self.core = build_discord()

    async def setup_hook(self):
        loaded_count = 0

        cog_specs = [
            (SpawnCog, (self.core,)),
            (EnergyCog, (self.core,)),
            (SelectCog, (self.core,)),
            (CaptureCog, (self.core,)),
            (ProfileCog, (self.core,)),
            (TrainerCog, (self.core,)),
            (IVsCog, (self.core,)),
            (InfoCog, (self.core,)),
            (PokedexCog, (self.core,)),
            (EvolutionCog, (self.core,)),
            (CandyCog, (self.core,)),
            (ReleaseCog, (self.core,)),
            (DuplicatesCog, (self.core,)),
            (TradeCog, (self.core,)),
            (CommandsCog, ()),
        ]

        for cog_class, args in cog_specs:
            logger.debug("Loading Discord cog %s", cog_class.__name__)
            cog = cog_class(*args)
            await self.add_cog(cog)
            logger.debug("Loaded Discord cog %s", cog_class.__name__)
            loaded_count += 1

        logger.info("Discord cogs loaded: %s", loaded_count)

    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
        command = getattr(ctx, "command", None)

        if command is not None and command.has_error_handler():
            return

        cog = getattr(ctx, "cog", None)

        if cog is not None and cog.has_error_handler():
            return

        if isinstance(
            error,
            (
                commands.CommandNotFound,
                commands.MissingRequiredArgument,
                commands.BadArgument,
                commands.CheckFailure,
            ),
        ):
            return

        command_name = command.qualified_name if command is not None else "<unknown>"
        guild_id = ctx.guild.id if getattr(ctx, "guild", None) is not None else None
        channel_id = (
            ctx.channel.id if getattr(ctx, "channel", None) is not None else None
        )
        user_id = ctx.author.id if getattr(ctx, "author", None) is not None else None

        if isinstance(error, commands.CommandInvokeError):
            original = error.original

            logger.error(
                "Unhandled command error command=%s guild=%s channel=%s user=%s",
                command_name,
                guild_id,
                channel_id,
                user_id,
                exc_info=(type(original), original, original.__traceback__),
            )
            return

        logger.error(
            (
                "Unhandled command framework error command=%s guild=%s "
                "channel=%s user=%s error_type=%s"
            ),
            command_name,
            guild_id,
            channel_id,
            user_id,
            type(error).__name__,
            exc_info=(type(error), error, error.__traceback__),
        )

    async def on_error(
        self,
        event_method: str,
        *args,
        **kwargs,
    ) -> None:
        logger.error(
            "Unhandled Discord event error event=%s",
            event_method,
            exc_info=sys.exc_info(),
        )


def create_bot() -> TicoMonBot:
    return TicoMonBot()
