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
        await self.add_cog(EnergyCog(self.core))
        await self.add_cog(SelectCog(self.core))
        await self.add_cog(CaptureCog(self.core))
        await self.add_cog(ProfileCog(self.core))
        await self.add_cog(TrainerCog(self.core))
        await self.add_cog(IVsCog(self.core))
        await self.add_cog(InfoCog(self.core))
        await self.add_cog(PokedexCog(self.core))
        await self.add_cog(EvolutionCog(self.core))
        await self.add_cog(CandyCog(self.core))
        await self.add_cog(ReleaseCog(self.core))
        await self.add_cog(DuplicatesCog(self.core))
        await self.add_cog(TradeCog(self.core))
        await self.add_cog(CommandsCog())


def create_bot() -> TicoMonBot:
    return TicoMonBot()
