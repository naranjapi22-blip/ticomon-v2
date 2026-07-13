from __future__ import annotations

import asyncio

import discord

from application.safari import SafariFinalSummary
from interfaces.discord.files import image_to_discord_file
from rendering.safari import SafariSummaryRenderer
from rendering.safari.narrative import summary_narrative


class SafariSummaryView(discord.ui.View):
    def __init__(self, finish_result) -> None:
        super().__init__(timeout=300)

        self.finish_result = finish_result
        self.summary: SafariFinalSummary = finish_result.summary
        self.message: discord.Message | None = None
        self.renderer = SafariSummaryRenderer()

    def build_embeds(self) -> tuple[discord.Embed, ...]:
        return (
            self._overview_embed(),
            self._ranking_embed(),
            self._route_embed(),
            self._encounters_embed(),
        )

    def _overview_embed(self) -> discord.Embed:
        summary = self.summary
        embed = discord.Embed(
            title="Safari Summary",
            description=summary_narrative(
                summary.finish_reason.value,
                summary.totals.encounters_completed,
            ),
            color=discord.Color.green(),
        )
        embed.set_image(url="attachment://safari-summary.png")
        embed.add_field(name="Map", value=summary.safari_map.value, inline=True)
        embed.add_field(name="Weather", value=summary.weather.value, inline=True)
        embed.add_field(name="Time", value=summary.time_of_day.value, inline=True)
        embed.add_field(
            name="Finish Reason",
            value=summary.finish_reason.value,
            inline=True,
        )
        embed.add_field(name="Level", value=str(summary.level), inline=True)
        embed.add_field(
            name="Totals",
            value=(
                f"Encounters: {summary.totals.encounters_completed}\n"
                f"Pokemon seen: {summary.totals.pokemon_seen}\n"
                f"Captured slots: {summary.totals.slots_captured}\n"
                f"Escaped slots: {summary.totals.slots_escaped}\n"
                f"Attempts: {summary.totals.attempts_executed}\n"
                f"Balls committed: {summary.totals.balls_committed}"
            ),
            inline=False,
        )
        embed.add_field(
            name="Extraordinary",
            value=(
                "Legendary: "
                f"{'Yes' if summary.extraordinary.legendary_seen else 'No'}\n"
                "Mythical: "
                f"{'Yes' if summary.extraordinary.mythical_seen else 'No'}\n"
                "Shiny global: "
                f"{'Yes' if summary.extraordinary.shiny_encounter_seen else 'No'}\n"
                "Regional herd: "
                f"{'Yes' if summary.extraordinary.regional_herd_seen else 'No'}"
            ),
            inline=False,
        )
        return embed

    async def build_file(self) -> discord.File:
        image = await asyncio.to_thread(self.renderer.render, self.summary)
        return image_to_discord_file(image, "safari-summary.png")

    def _ranking_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Safari Ranking",
            color=discord.Color.blurple(),
        )
        for participant in self.summary.ranking:
            captures = (
                "\n".join(
                    (
                        f"#{creature.collection_number} - "
                        f"{creature.species.name.title()}"
                        + (" [shiny]" if creature.is_shiny else "")
                        + (
                            f" ({creature.current_form.name})"
                            if creature.current_form is not None
                            else ""
                        )
                    )
                    for creature in participant.captured_creatures
                )
                or "No captures."
            )
            embed.add_field(
                name=f"#{participant.rank} <@{participant.trainer_id}>",
                value=(
                    f"Captures: {participant.capture_count}\n"
                    f"Shiny: {participant.shiny_capture_count}\n"
                    f"Balls used: {participant.balls_used}\n"
                    f"Balls remaining: {participant.balls_remaining}\n"
                    f"Attempts: {participant.attempts_executed}\n"
                    f"Slots won: {participant.slots_won}\n"
                    f"Encounters: {participant.encounters_participated}\n"
                    f"Captures:\n{captures}"
                ),
                inline=False,
            )
        return embed

    def _route_embed(self) -> discord.Embed:
        summary = self.summary
        embed = discord.Embed(
            title="Safari Route",
            color=discord.Color.gold(),
        )
        embed.add_field(name="Map", value=summary.route.safari_map.value, inline=True)
        embed.add_field(name="Weather", value=summary.route.weather.value, inline=True)
        embed.add_field(
            name="Time",
            value=summary.route.time_of_day.value,
            inline=True,
        )
        for index, segment in enumerate(summary.route.segments, start=1):
            details = [
                f"Phase: {segment.phase.value}",
                f"Remaining encounters: {segment.remaining_encounters}",
                f"Source option: {segment.source_option_id or 'Initial'}",
            ]
            if segment.vote_result is not None:
                details.append(
                    "Selected option: " f"{segment.vote_result.selected_option.id}"
                )
            embed.add_field(
                name=f"Segment {index} - {segment.zone.value}",
                value="\n".join(details),
                inline=False,
            )
        return embed

    def _encounters_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Safari Encounters",
            color=discord.Color.purple(),
        )
        for index, encounter in enumerate(self.summary.encounters, start=1):
            slot_lines = []
            for slot in encounter.slot_summaries:
                capture_text = "Escaped"
                if slot.captured_creature is not None:
                    capture_text = (
                        f"Captured #{slot.captured_creature.collection_number} "
                        f"by <@{slot.captured_creature.trainer_id}>"
                    )
                slot_lines.append(
                    f"Slot {slot.slot_id}: {slot.species.name.title()} - "
                    f"{capture_text}"
                )
            embed.add_field(
                name=f"Encounter {index}",
                value="\n".join(slot_lines),
                inline=False,
            )
        return embed
