from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import ImageDraw, ImageFont

from rendering.battle.frame_state import BattleFrameState
from rendering.battle.layout import HEIGHT, MARGIN, WIDTH

BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
HP_BAR_YELLOW = (255, 204, 0, 255)
HP_BAR_EMPTY = (80, 80, 80, 255)
HP_BAR_BORDER = (40, 40, 40, 255)

TRAINER_FONT_SIZE = 28
POKEMON_FONT_SIZE = 24
HP_TEXT_FONT_SIZE = 20
TEXT_OUTLINE_WIDTH = 2
HP_BAR_WIDTH = 240
HP_BAR_HEIGHT = 16


@dataclass(frozen=True)
class BattleFonts:
    trainer: ImageFont.FreeTypeFont | ImageFont.ImageFont
    pokemon: ImageFont.FreeTypeFont | ImageFont.ImageFont
    hp_text: ImageFont.FreeTypeFont | ImageFont.ImageFont


def draw_battle_hud(
    draw: ImageDraw.ImageDraw,
    frame: BattleFrameState,
    fonts: BattleFonts,
) -> None:
    _draw_hp_bar(
        draw,
        anchor_x=MARGIN,
        y=36,
        align="left",
        label=frame.side_b_name,
        pokemon_name=frame.side_b_active_name,
        hp=frame.side_b_hp,
        hp_max=frame.side_b_hp_max,
        trainer_font=fonts.trainer,
        pokemon_font=fonts.pokemon,
        hp_text_font=fonts.hp_text,
    )
    _draw_hp_bar(
        draw,
        anchor_x=WIDTH - MARGIN,
        y=HEIGHT - 150,
        align="right",
        label=frame.side_a_name,
        pokemon_name=frame.side_a_active_name,
        hp=frame.side_a_hp,
        hp_max=frame.side_a_hp_max,
        trainer_font=fonts.trainer,
        pokemon_font=fonts.pokemon,
        hp_text_font=fonts.hp_text,
    )


def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    *,
    anchor: str | None = None,
) -> None:
    draw.text(
        xy,
        text,
        fill=BLACK,
        font=font,
        anchor=anchor,
        stroke_width=TEXT_OUTLINE_WIDTH,
        stroke_fill=WHITE,
    )


def _text_size(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    left, top, right, bottom = font.getbbox(text)
    return right - left, bottom - top


def _draw_hp_bar(
    draw: ImageDraw.ImageDraw,
    *,
    anchor_x: int,
    y: int,
    align: Literal["left", "right"],
    label: str,
    pokemon_name: str,
    hp: int,
    hp_max: int,
    trainer_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    pokemon_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    hp_text_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    trainer_anchor = "lt" if align == "left" else "rt"
    pokemon_anchor = trainer_anchor

    _draw_outlined_text(
        draw,
        (anchor_x, y),
        label,
        trainer_font,
        anchor=trainer_anchor,
    )

    trainer_height = _text_size(label, trainer_font)[1]
    pokemon_y = y + trainer_height + 6
    _draw_outlined_text(
        draw,
        (anchor_x, pokemon_y),
        pokemon_name,
        pokemon_font,
        anchor=pokemon_anchor,
    )

    pokemon_height = _text_size(pokemon_name, pokemon_font)[1]
    bar_y = pokemon_y + pokemon_height + 8
    if align == "left":
        bar_x = anchor_x
    else:
        bar_x = anchor_x - HP_BAR_WIDTH

    fraction = 0 if hp_max <= 0 else max(0.0, min(1.0, hp / hp_max))
    fill_width = int(HP_BAR_WIDTH * fraction)

    draw.rectangle(
        (bar_x, bar_y, bar_x + HP_BAR_WIDTH, bar_y + HP_BAR_HEIGHT),
        fill=HP_BAR_EMPTY,
        outline=HP_BAR_BORDER,
    )
    if fill_width > 0:
        draw.rectangle(
            (bar_x, bar_y, bar_x + fill_width, bar_y + HP_BAR_HEIGHT),
            fill=HP_BAR_YELLOW,
        )

    hp_label = f"{hp}/{hp_max}"
    if align == "left":
        hp_x = bar_x + HP_BAR_WIDTH + 8
        hp_anchor = "lt"
    else:
        hp_x = bar_x - 8
        hp_anchor = "rt"

    _draw_outlined_text(
        draw,
        (hp_x, bar_y - 2),
        hp_label,
        hp_text_font,
        anchor=hp_anchor,
    )
