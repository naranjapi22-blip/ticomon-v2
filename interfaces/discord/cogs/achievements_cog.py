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
        unlocked: dict[str, list[str]] = {}
        progress: dict[str, list[str]] = {}
        for status in statuses:
            bucket = unlocked if status.unlocked else progress
            lines = bucket.setdefault(status.family, [])
            if status.unlocked:
                candies = ", ".join(
                    f"{kind.value.title()} +{amount}"
                    for kind, amount in status.rewarded_candies.items()
                )
                lines.append(
                    f"**{status.name}** — {status.description}\n"
                    f"Unlocked: {status.unlocked_at:%Y-%m-%d} • {candies}"
                )
            else:
                lines.append(
                    f"**{status.name}** — {status.description}\n"
                    f"{status.progress} / {status.threshold} • Reward: "
                    f"{status.configured_reward} candies"
                )
        for section, groups in (("Unlocked", unlocked), ("In progress", progress)):
            embed = discord.Embed(
                title=f"Achievements — {section}", color=discord.Color.gold()
            )
            if not groups:
                embed.add_field(name=section, value="None", inline=False)
            else:
                for family, lines in groups.items():
                    embed.add_field(
                        name=family, value="\n\n".join(lines)[:1024], inline=False
                    )
            await ctx.send(embed=embed)
