from __future__ import annotations

import textwrap

from PIL import Image, ImageDraw, ImageOps

from application.safari import SafariFinalSummary
from core.safari import SafariSession
from core.safari.domain import SAFARI_ZONE_DEFINITION_BY_ZONE, SafariMap

from .assets import SafariAssets
from .layout import SlotPlacement, layout_slot_cards
from .narrative import summary_narrative

CANVAS_SIZE = (1020, 574)


class SafariEncounterRenderer:
    def __init__(self, assets: SafariAssets | None = None) -> None:
        self.assets = assets or SafariAssets()

    def render(self, session: SafariSession) -> Image.Image:
        encounter = session.current_encounter
        if encounter is None:
            raise ValueError("Safari encounter is required.")

        canvas = self._background(session)
        draw = ImageDraw.Draw(canvas)

        placements = layout_slot_cards(len(encounter.slots))
        for slot, placement in zip(encounter.slots, placements):
            self._draw_slot_card(draw, canvas, slot, placement)
        return canvas

    def _background(self, session: SafariSession) -> Image.Image:
        background_name = self._background_name(session)
        background_loader = getattr(self.assets, "get_background_by_name", None)
        if background_name is None or background_loader is None:
            background = self.assets.get_background(session.safari_map).copy()
        else:
            background = background_loader(background_name).copy()
        background = background.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)

        overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            (0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1]), fill=(0, 0, 0, 52)
        )
        return Image.alpha_composite(background, overlay)

    @staticmethod
    def _background_name(session: SafariSession) -> str | None:
        current_segment = getattr(session, "current_segment", None)
        zone = getattr(current_segment, "zone", None)
        if zone is None:
            return {
                SafariMap.FOREST: "grass",
                SafariMap.MOUNTAIN: "rock",
                SafariMap.COAST: "water",
                SafariMap.SWAMP: "poison",
                SafariMap.PLAINS: "normal",
            }.get(session.safari_map)

        definition = SAFARI_ZONE_DEFINITION_BY_ZONE[zone]
        map_background = {
            SafariMap.FOREST: "grass",
            SafariMap.MOUNTAIN: "rock",
            SafariMap.COAST: "water",
            SafariMap.SWAMP: "poison",
            SafariMap.PLAINS: "normal",
        }.get(session.safari_map)
        ordered_types = sorted(
            definition.base_type_weights.items(),
            key=lambda item: (-item[1], item[0]),
        )
        for type_name, _ in ordered_types:
            if type_name != map_background:
                return type_name
        return map_background

    def _draw_slot_card(
        self,
        draw: ImageDraw.ImageDraw,
        canvas: Image.Image,
        slot,
        placement: SlotPlacement,
    ) -> None:
        card = Image.new("RGBA", (placement.width, placement.height), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card)

        name = self.format_species_name(slot.opportunity.species.name)
        name_font = self._name_font_for(name, placement.width)

        sprite = self.assets.get_sprite(
            slot.opportunity.species.id,
            slot.opportunity.is_shiny,
        ).copy()
        sprite = ImageOps.contain(
            sprite, (placement.width - 40, placement.height - 124)
        )
        sprite_x = (placement.width - sprite.width) // 2
        sprite_y = 68
        card.paste(sprite, (sprite_x, sprite_y), sprite)

        wrapped_name = self._wrap_name(
            name, width=self._name_wrap_width(placement.width)
        )
        bbox = card_draw.multiline_textbbox(
            (0, 0), wrapped_name, font=name_font, spacing=2
        )
        text_x = (placement.width - (bbox[2] - bbox[0])) // 2
        text_y = placement.height - 44
        card_draw.multiline_text(
            (text_x, text_y),
            wrapped_name,
            font=name_font,
            fill="white",
            align="center",
            spacing=2,
        )

        canvas.alpha_composite(card, (placement.x, placement.y))

    @staticmethod
    def format_species_name(name: str) -> str:
        parts = [part for part in name.replace("_", "-").split("-") if part]
        if len(parts) >= 2 and len(parts[0]) > 3:
            suffix = "-".join(part.title() for part in parts[1:])
            return f"{parts[0].title()} ({suffix})"
        return " ".join(part.title() for part in parts) or name.title()

    def _name_font_for(self, name: str, width: int):
        font_size = 24
        while font_size > 14:
            font = self.assets.get_font(font_size)
            bbox = font.getbbox(name)
            if bbox[2] - bbox[0] <= width - 34:
                return font
            font_size -= 2
        return self.assets.get_font(14)

    @staticmethod
    def _name_wrap_width(width: int) -> int:
        if width >= 600:
            return 24
        if width >= 400:
            return 20
        return 18

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
