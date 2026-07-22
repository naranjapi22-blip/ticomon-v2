from types import SimpleNamespace

from interfaces.discord.cogs.pvp_cog import PvpCog


def test_pvp_cog_registers_experimental_command_without_replacing_pvp():
    cog = PvpCog(SimpleNamespace())
    commands = {command.name: command for command in cog.get_commands()}

    assert set(commands) == {"pvp", "pvptest"}
    assert commands["pvp"].callback is not commands["pvptest"].callback
