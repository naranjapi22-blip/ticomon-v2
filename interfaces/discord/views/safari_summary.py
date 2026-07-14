from __future__ import annotations

import asyncio

import discord

from application.safari import SafariFinalSummary
from core.safari.domain import SafariFinishReason
from interfaces.discord.files import image_to_discord_file
from rendering.safari import SafariSummaryRenderer


class SafariSummaryView(discord.ui.View):
    def __init__(self, finish_result) -> None:
        super().__init__(timeout=300)

        self.finish_result = finish_result
        self.summary: SafariFinalSummary = finish_result.summary
        self.message: discord.Message | None = None
        self.renderer = SafariSummaryRenderer()

    def build_embeds(self) -> tuple[discord.Embed, ...]:
        embeds = [self._overview_embed(), self._ranking_embed()]
        special_encounters = self._special_encounters_embed()
        if special_encounters is not None:
            embeds.append(special_encounters)
        return tuple(embeds)

    def _overview_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Safari Complete",
            description=self._build_overview_description(),
            color=discord.Color.green(),
        )
        embed.set_image(url="attachment://safari-summary.png")
        embed.add_field(
            name="Results",
            value=(
                f"Pokémon captured: {self._captured_count()}\n"
                f"Safari Balls used: {self._balls_used()}\n"
                f"Safari Balls remaining: {self._balls_remaining()}"
            ),
            inline=False,
        )

        captured_lines = self._captured_pokemon_lines()
        if captured_lines:
            embed.add_field(
                name="Captured Pokémon",
                value="\n".join(captured_lines),
                inline=False,
            )

        return embed

    async def build_file(self) -> discord.File:
        image = await asyncio.to_thread(self.renderer.render, self.summary)
        return image_to_discord_file(image, "safari-summary.png")

    def _ranking_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Ranking",
            color=discord.Color.blurple(),
        )
        lines = [
            (
                f"{participant.rank}. <@{participant.trainer_id}> — "
                f"{participant.capture_count} capture"
                f"{'s' if participant.capture_count != 1 else ''}"
            )
            for participant in self.summary.ranking
        ]
        embed.description = "\n".join(lines) if lines else "No participants recorded."
        return embed

    def _special_encounters_embed(self) -> discord.Embed | None:
        lines = []
        if self.summary.extraordinary.legendary_seen:
            lines.append("• Legendary Pokémon appeared")
        if self.summary.extraordinary.mythical_seen:
            lines.append("• Mythical Pokémon appeared")
        if self.summary.extraordinary.shiny_encounter_seen:
            lines.append("• Global shiny encounter")
        if self.summary.extraordinary.regional_herd_seen:
            lines.append("• Regional herd")

        if not lines:
            return None

        embed = discord.Embed(
            title="Special Encounters",
            color=discord.Color.purple(),
        )
        embed.description = "\n".join(lines)
        return embed

    def _build_overview_description(self) -> str:
        summary = self.summary
        context = " · ".join(
            (
                summary.safari_map.value.title(),
                summary.weather.value.title(),
                summary.time_of_day.value.title(),
            )
        )
        return (
            f"{context}\n"
            f"{self._finish_reason_text()}\n"
            f"The expedition ended after {summary.totals.encounters_completed} "
            f"encounter{'s' if summary.totals.encounters_completed != 1 else ''}."
        )

    def _captured_pokemon_lines(self) -> list[str]:
        lines: list[str] = []
        for participant in self.summary.ranking:
            for creature in participant.captured_creatures:
                name = creature.species.name.title()
                if creature.current_form is not None:
                    name = f"{name} ({creature.current_form.name})"
                if creature.is_shiny:
                    name = f"{name} [shiny]"
                lines.append(f"{name} · #{creature.collection_number}")
        return lines

    def _captured_count(self) -> int:
        return sum(participant.capture_count for participant in self.summary.ranking)

    def _balls_used(self) -> int:
        return sum(participant.balls_used for participant in self.summary.ranking)

    def _balls_remaining(self) -> int:
        return sum(participant.balls_remaining for participant in self.summary.ranking)

    def _finish_reason_text(self) -> str:
        reason = self.summary.finish_reason
        if reason is SafariFinishReason.COMPLETED:
            return "The expedition was completed successfully."
        if reason is SafariFinishReason.NO_BALLS_REMAINING:
            return "The expedition ended because no Safari Balls remained."
        if reason is SafariFinishReason.ADMINISTRATIVE_ABORT:
            return "The expedition was ended by an administrator."
        return "The expedition ended."
