import discord
from discord.ext import commands

from interfaces.discord.bootstrap import build_discord
from interfaces.discord.cogs.capture_cog import CaptureCog
from interfaces.discord.cogs.spawn_cog import SpawnCog


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
        await self.add_cog(SpawnCog(self.core))
        await self.add_cog(CaptureCog(self.core))


def create_bot() -> TicoMonBot:
    return TicoMonBot()
