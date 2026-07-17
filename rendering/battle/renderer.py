from __future__ import annotations

from io import BytesIO
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

from rendering.battle.assets import HEIGHT, WIDTH, BattleAssets
from rendering.battle.frame_state import BattleFrameState

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
MARGIN = 36
OPPONENT_SPRITE_MAX_SIZE = 374
PLAYER_SPRITE_MAX_SIZE = 528
OPPONENT_SPRITE_ANCHOR = (930, 100)
PLAYER_SPRITE_ANCHOR = (70, HEIGHT - 30)


class BattleRenderer:
    def __init__(self) -> None:
        self._assets = BattleAssets()

    def get_background_for_battle(self, battle_id: int) -> Image.Image:
        return self._assets.get_background_for_battle(battle_id)

    def render(
        self,
        frame: BattleFrameState,
        *,
        background: Image.Image | None = None,
    ) -> Image.Image:
        canvas = (
            background.copy()
            if background is not None
            else self._assets.get_background().copy()
        )
        draw = ImageDraw.Draw(canvas)
        trainer_font = self._assets.get_font(TRAINER_FONT_SIZE)
        pokemon_font = self._assets.get_font(POKEMON_FONT_SIZE)
        hp_text_font = self._assets.get_font(HP_TEXT_FONT_SIZE)

        self._draw_sprite(
            canvas,
            frame.side_b_pokeapi_id,
            shiny=frame.side_b_shiny,
            anchor=OPPONENT_SPRITE_ANCHOR,
            anchor_mode="top_right",
            max_size=OPPONENT_SPRITE_MAX_SIZE,
            flip=False,
        )
        self._draw_sprite(
            canvas,
            frame.side_a_pokeapi_id,
            shiny=frame.side_a_shiny,
            anchor=PLAYER_SPRITE_ANCHOR,
            anchor_mode="bottom_left",
            max_size=PLAYER_SPRITE_MAX_SIZE,
            flip=True,
        )

        self._draw_hp_bar(
            draw,
            anchor_x=MARGIN,
            y=36,
            align="left",
            label=frame.side_b_name,
            pokemon_name=frame.side_b_active_name,
            hp=frame.side_b_hp,
            hp_max=frame.side_b_hp_max,
            trainer_font=trainer_font,
            pokemon_font=pokemon_font,
            hp_text_font=hp_text_font,
        )
        self._draw_hp_bar(
            draw,
            anchor_x=WIDTH - MARGIN,
            y=HEIGHT - 150,
            align="right",
            label=frame.side_a_name,
            pokemon_name=frame.side_a_active_name,
            hp=frame.side_a_hp,
            hp_max=frame.side_a_hp_max,
            trainer_font=trainer_font,
            pokemon_font=pokemon_font,
            hp_text_font=hp_text_font,
        )

        return canvas

    def render_to_bytes(
        self,
        frame: BattleFrameState,
        *,
        background: Image.Image | None = None,
    ) -> bytes:
        image = self.render(frame, background=background)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _draw_sprite(
        self,
        canvas: Image.Image,
        pokeapi_id: int,
        *,
        shiny: bool,
        anchor: tuple[int, int],
        anchor_mode: Literal["bottom_left", "top_right"],
        max_size: int,
        flip: bool,
    ) -> None:
        sprite = self._scale_sprite(
            self._assets.get_sprite(pokeapi_id, shiny=shiny).copy(),
            max_size,
        )
        if flip:
            sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        content_bbox = sprite.getbbox()
        if content_bbox is None:
            return

        content_left, content_top, content_right, content_bottom = content_bbox
        anchor_x, anchor_y = anchor
        if anchor_mode == "bottom_left":
            position = (anchor_x - content_left, anchor_y - content_bottom)
        else:
            position = (anchor_x - content_right, anchor_y - content_top)

        canvas.paste(sprite, position, sprite)

    @staticmethod
    def _scale_sprite(sprite: Image.Image, max_size: int) -> Image.Image:
        scale = min(max_size / sprite.width, max_size / sprite.height)
        if scale <= 0:
            return sprite
        new_width = max(int(sprite.width * scale), 1)
        new_height = max(int(sprite.height * scale), 1)
        if new_width == sprite.width and new_height == sprite.height:
            return sprite
        return sprite.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _draw_outlined_text(
        self,
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
        self,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    ) -> tuple[int, int]:
        left, top, right, bottom = font.getbbox(text)
        return right - left, bottom - top

    def _draw_hp_bar(
        self,
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

        self._draw_outlined_text(
            draw,
            (anchor_x, y),
            label,
            trainer_font,
            anchor=trainer_anchor,
        )

        trainer_height = self._text_size(label, trainer_font)[1]
        pokemon_y = y + trainer_height + 6
        self._draw_outlined_text(
            draw,
            (anchor_x, pokemon_y),
            pokemon_name,
            pokemon_font,
            anchor=pokemon_anchor,
        )

        pokemon_height = self._text_size(pokemon_name, pokemon_font)[1]
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

        self._draw_outlined_text(
            draw,
            (hp_x, bar_y - 2),
            hp_label,
            hp_text_font,
            anchor=hp_anchor,
        )
