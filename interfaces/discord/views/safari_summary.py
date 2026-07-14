from __future__ import annotations

import discord

from application.safari import SafariFinalSummary


class SafariSummaryView(discord.ui.View):
    def __init__(self, finish_result) -> None:
        super().__init__(timeout=300)

        self.finish_result = finish_result
        self.summary: SafariFinalSummary = finish_result.summary
        self.message: discord.Message | None = None

    def build_embeds(self) -> tuple[discord.Embed, ...]:
        embed = discord.Embed(
            title="Safari Complete",
            color=discord.Color.green(),
        )

        top_captures = self._top_capture_lines()
        if top_captures:
            embed.description = "Top Captures\n" + "\n".join(top_captures)
        else:
            embed.description = "No Pokémon were captured during this expedition."

        return (embed,)

    def _top_capture_lines(self) -> list[str]:
        lines: list[str] = []
        for participant in self.summary.ranking[:3]:
            lines.append(
                f"{participant.rank}. <@{participant.trainer_id}> — "
                f"{participant.capture_count}"
            )
        return lines
