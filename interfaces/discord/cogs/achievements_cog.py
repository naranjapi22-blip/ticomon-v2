import discord
from discord.ext import commands


class AchievementsCog(commands.Cog):
    def __init__(self, core) -> None:
        self._core = core

    @commands.command(name="achievements")
    async def achievements(self, ctx) -> None:
        statuses = await self._core.achievement_query_service.get_for_trainer(
            ctx.author.id
        )
        unlocked = []
        progress = []
        for status in statuses:
            if status.unlocked:
                candies = ", ".join(
                    f"{kind.value.title()} +{amount}"
                    for kind, amount in status.rewarded_candies.items()
                )
                unlocked.append(
                    f"**{status.name}** — {status.description}\n"
                    f"Unlocked: {status.unlocked_at:%Y-%m-%d} • {candies}"
                )
            else:
                progress.append(
                    f"**{status.name}** — {status.description}\n"
                    f"{status.progress} / {status.threshold} • Reward: "
                    f"{status.configured_reward} candies"
                )
        embed = discord.Embed(title="Achievements", color=discord.Color.gold())
        embed.add_field(
            name="Unlocked", value="\n\n".join(unlocked) or "None", inline=False
        )
        embed.add_field(
            name="In progress", value="\n\n".join(progress) or "None", inline=False
        )
        await ctx.send(embed=embed)
