from __future__ import annotations

import textwrap
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageOps

from application.safari import SafariFinalSummary
from core.safari import SafariSession
from core.safari.domain import SafariMap

from .assets import SafariAssets
from .layout import SlotPlacement, layout_slot_cards
from .narrative import encounter_narrative, summary_narrative

CANVAS_SIZE = (1020, 574)


@dataclass(frozen=True, slots=True)
class _Palette:
    border: tuple[int, int, int, int]
    fill: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]


PALETTE = _Palette(
    border=(255, 255, 255, 220),
    fill=(12, 16, 20, 178),
    accent=(255, 215, 0, 255),
)


class SafariEncounterRenderer:
    def __init__(self, assets: SafariAssets | None = None) -> None:
        self.assets = assets or SafariAssets()

    def render(self, session: SafariSession) -> Image.Image:
        encounter = session.current_encounter
        if encounter is None:
            raise ValueError("Safari encounter is required.")

        canvas = self._background(session.safari_map)
        draw = ImageDraw.Draw(canvas)

        self._draw_header(
            draw,
            session.safari_map.value.title(),
            session.weather.value.title(),
            session.time_of_day.value.title(),
            session.phase.value.title(),
            session.completed_encounter_count + 1,
            session.total_encounters,
        )

        narrative = encounter_narrative(
            session.safari_map,
            session.weather,
            session.time_of_day,
            session.phase,
        )
        self._draw_narrative(draw, narrative)

        placements = layout_slot_cards(len(encounter.slots))
        for index, (slot, placement) in enumerate(
            zip(encounter.slots, placements), start=1
        ):
            self._draw_slot_card(draw, canvas, slot, placement, index)

        self._draw_footer(draw, session.current_segment.remaining_encounters)
        return canvas

    def _background(self, safari_map: SafariMap) -> Image.Image:
        background = self.assets.get_background(safari_map).copy()
        background = background.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)

        overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle((0, 0, CANVAS_SIZE[0], 140), fill=(0, 0, 0, 92))
        overlay_draw.rectangle(
            (0, CANVAS_SIZE[1] - 78, CANVAS_SIZE[0], CANVAS_SIZE[1]),
            fill=(0, 0, 0, 96),
        )
        return Image.alpha_composite(background, overlay)

    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        safari_map: str,
        weather: str,
        time_of_day: str,
        phase: str,
        encounter_number: int,
        total_encounters: int,
    ) -> None:
        title_font = self.assets.get_font(28)
        body_font = self.assets.get_font(16)
        small_font = self.assets.get_font(13)

        draw.text((32, 18), f"{safari_map} Safari", font=title_font, fill="white")
        draw.text(
            (32, 58),
            f"{weather} • {time_of_day} • Phase {phase}",
            font=body_font,
            fill=(235, 240, 245, 255),
        )
        draw.text(
            (32, 82),
            f"Encounter {encounter_number} / {total_encounters}",
            font=body_font,
            fill=(235, 240, 245, 255),
        )

        bar_x = 32
        bar_y = 112
        bar_w = 440
        bar_h = 14
        progress = max(0.0, min(1.0, encounter_number / max(total_encounters, 1)))
        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + bar_w, bar_y + bar_h),
            radius=7,
            fill=(255, 255, 255, 42),
        )
        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + int(bar_w * progress), bar_y + bar_h),
            radius=7,
            fill=PALETTE.accent,
        )

        draw.text(
            (bar_x + bar_w + 18, bar_y - 1),
            f"{int(progress * 100)}%",
            font=small_font,
            fill="white",
        )

    def _draw_narrative(self, draw: ImageDraw.ImageDraw, narrative: str) -> None:
        font = self.assets.get_font(15)
        wrapped = "\n".join(textwrap.wrap(narrative, width=96))
        draw.multiline_text((32, 145), wrapped, font=font, fill=(248, 248, 248, 235))

    def _draw_footer(
        self, draw: ImageDraw.ImageDraw, remaining_encounters: int
    ) -> None:
        font = self.assets.get_font(15)
        draw.text(
            (32, CANVAS_SIZE[1] - 54),
            f"{remaining_encounters} encounter(s) left in the current route segment.",
            font=font,
            fill="white",
        )

    def _draw_slot_card(
        self,
        draw: ImageDraw.ImageDraw,
        canvas: Image.Image,
        slot,
        placement: SlotPlacement,
        index: int,
    ) -> None:
        card = Image.new("RGBA", (placement.width, placement.height), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card)

        shiny = slot.opportunity.is_shiny
        border_color = PALETTE.accent if shiny else PALETTE.border
        fill_color = (24, 30, 35, 210) if shiny else PALETTE.fill
        card_draw.rounded_rectangle(
            (0, 0, placement.width - 1, placement.height - 1),
            radius=24,
            fill=fill_color,
            outline=border_color,
            width=3,
        )

        number_font = self.assets.get_font(22)
        name_font = self.assets.get_font(18)
        tag_font = self.assets.get_font(12)

        card_draw.rounded_rectangle(
            (16, 14, 56, 54),
            radius=12,
            fill=border_color,
        )
        number_text = str(index)
        bbox = card_draw.textbbox((0, 0), number_text, font=number_font)
        card_draw.text(
            (
                16 + (40 - (bbox[2] - bbox[0])) // 2,
                14 + (40 - (bbox[3] - bbox[1])) // 2 - 2,
            ),
            number_text,
            font=number_font,
            fill=(0, 0, 0, 255),
        )

        sprite = self.assets.get_sprite(slot.opportunity.species.id, shiny).copy()
        sprite = ImageOps.contain(sprite, (placement.width - 70, placement.height - 90))
        sprite_x = (placement.width - sprite.width) // 2
        sprite_y = 42
        card.paste(sprite, (sprite_x, sprite_y), sprite)

        species_name = slot.opportunity.species.name.title()
        name = self._wrap_name(species_name, width=18)
        bbox = card_draw.multiline_textbbox((0, 0), name, font=name_font, spacing=2)
        text_x = (placement.width - (bbox[2] - bbox[0])) // 2
        text_y = placement.height - 60
        card_draw.multiline_text(
            (text_x, text_y),
            name,
            font=name_font,
            fill="white",
            align="center",
            spacing=2,
        )

        tag_x = placement.width // 2
        tag_y = placement.height - 28
        tag = "Shiny" if shiny else "Wild"
        if slot.opportunity.initial_form is not None:
            tag = f"{slot.opportunity.initial_form.name.title()} • {tag}"
        self._draw_tag(card_draw, tag_x, tag_y, tag, tag_font)

        canvas.alpha_composite(card, (placement.x, placement.y))

    def _draw_tag(
        self,
        draw: ImageDraw.ImageDraw,
        center_x: int,
        center_y: int,
        text: str,
        font,
    ) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0] + 24
        height = bbox[3] - bbox[1] + 14
        left = center_x - width // 2
        top = center_y - height // 2
        draw.rounded_rectangle(
            (left, top, left + width, top + height),
            radius=12,
            fill=(0, 0, 0, 120),
            outline=(255, 255, 255, 80),
        )
        draw.text(
            (
                left + 12,
                top + 7,
            ),
            text,
            font=font,
            fill="white",
        )

    @staticmethod
    def _wrap_name(name: str, width: int) -> str:
        return "\n".join(textwrap.wrap(name, width=width)) or name


class SafariSummaryRenderer:
    def __init__(self, assets: SafariAssets | None = None) -> None:
        self.assets = assets or SafariAssets()

    def render(self, summary: SafariFinalSummary) -> Image.Image:
        canvas = self.assets.get_background(summary.safari_map).copy()
        canvas = canvas.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
        overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            (0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1]), fill=(0, 0, 0, 84)
        )
        overlay_draw.rounded_rectangle(
            (24, 24, CANVAS_SIZE[0] - 24, 176),
            radius=26,
            fill=(12, 16, 20, 194),
            outline=(255, 255, 255, 110),
            width=3,
        )
        overlay_draw.rounded_rectangle(
            (24, 196, 498, 548),
            radius=26,
            fill=(12, 16, 20, 194),
            outline=(255, 255, 255, 110),
            width=3,
        )
        overlay_draw.rounded_rectangle(
            (522, 196, 996, 548),
            radius=26,
            fill=(12, 16, 20, 194),
            outline=(255, 255, 255, 110),
            width=3,
        )
        canvas = Image.alpha_composite(canvas, overlay)

        draw = ImageDraw.Draw(canvas)
        title_font = self.assets.get_font(30)
        body_font = self.assets.get_font(16)
        small_font = self.assets.get_font(13)

        draw.text(
            (40, 38),
            "Safari Expedition Complete",
            font=title_font,
            fill="white",
        )
        draw.text(
            (40, 82),
            summary_narrative(
                summary.finish_reason.value,
                summary.totals.encounters_completed,
            ),
            font=body_font,
            fill=(240, 240, 240, 255),
        )
        draw.text(
            (40, 118),
            (
                f"Map: {summary.safari_map.value.title()} "
                f"? Weather: {summary.weather.value.title()} "
                f"? Time: {summary.time_of_day.value.title()}"
            ),
            font=body_font,
            fill=(240, 240, 240, 255),
        )
        draw.text(
            (40, 146),
            f"Started: {summary.started_at.isoformat()}",
            font=small_font,
            fill=(220, 220, 220, 255),
        )
        draw.text(
            (40, 166),
            f"Finished: {summary.finished_at.isoformat()}",
            font=small_font,
            fill=(220, 220, 220, 255),
        )

        self._draw_overview(draw, summary)
        self._draw_ranking(draw, summary)
        return canvas

    def _draw_overview(
        self, draw: ImageDraw.ImageDraw, summary: SafariFinalSummary
    ) -> None:
        heading_font = self.assets.get_font(18)
        body_font = self.assets.get_font(14)
        draw.text((44, 214), "Overview", font=heading_font, fill="white")
        lines = [
            f"Finish reason: {summary.finish_reason.value.replace('_', ' ').title()}",
            f"Encounters completed: {summary.totals.encounters_completed}",
            f"Pokemon seen: {summary.totals.pokemon_seen}",
            f"Captured slots: {summary.totals.slots_captured}",
            f"Escaped slots: {summary.totals.slots_escaped}",
            f"Attempts executed: {summary.totals.attempts_executed}",
            f"Balls committed: {summary.totals.balls_committed}",
            (
                "Legendary observed: "
                f"{'Yes' if summary.extraordinary.legendary_seen else 'No'}"
            ),
            (
                "Mythical observed: "
                f"{'Yes' if summary.extraordinary.mythical_seen else 'No'}"
            ),
            (
                "Shiny global observed: "
                f"{'Yes' if summary.extraordinary.shiny_encounter_seen else 'No'}"
            ),
            (
                "Regional herd observed: "
                f"{'Yes' if summary.extraordinary.regional_herd_seen else 'No'}"
            ),
        ]
        draw.multiline_text(
            (44, 250),
            "\n".join(lines),
            font=body_font,
            fill=(240, 240, 240, 255),
            spacing=4,
        )

        route_text = "Route: " + " → ".join(
            segment.zone.value.replace("_", " ").title()
            for segment in summary.route.segments
        )
        wrapped = "\n".join(textwrap.wrap(route_text, width=54))
        draw.text((44, 460), "Route", font=heading_font, fill="white")
        draw.multiline_text(
            (44, 490),
            wrapped,
            font=body_font,
            fill=(240, 240, 240, 255),
            spacing=4,
        )

    def _draw_ranking(
        self, draw: ImageDraw.ImageDraw, summary: SafariFinalSummary
    ) -> None:
        heading_font = self.assets.get_font(18)
        body_font = self.assets.get_font(14)
        draw.text((542, 214), "Ranking", font=heading_font, fill="white")

        lines: list[str] = []
        for participant in summary.ranking[:6]:
            lines.append(
                f"#{participant.rank} <@{participant.trainer_id}> "
                f"• {participant.capture_count} captures • "
                f"{participant.shiny_capture_count} shiny • "
                f"{participant.balls_remaining} balls left"
            )

        if not lines:
            lines.append("No participants recorded.")

        draw.multiline_text(
            (542, 250),
            "\n".join(lines),
            font=body_font,
            fill=(240, 240, 240, 255),
            spacing=6,
        )

        draw.text((542, 390), "Top captures", font=heading_font, fill="white")
        capture_lines: list[str] = []
        for participant in summary.ranking[:4]:
            for creature in participant.captured_creatures[:2]:
                line = (
                    f"#{creature.collection_number} {creature.species.name.title()}"
                    + (" [shiny]" if creature.is_shiny else "")
                )
                if creature.current_form is not None:
                    line += f" ({creature.current_form.name})"
                capture_lines.append(line)

        if not capture_lines:
            capture_lines.append("No captures recorded.")

        draw.multiline_text(
            (542, 426),
            "\n".join(capture_lines[:6]),
            font=body_font,
            fill=(240, 240, 240, 255),
            spacing=4,
        )
