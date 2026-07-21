from __future__ import annotations

import logging

from PIL import Image, ImageDraw

from rendering.battle.assets import BattleAssets
from rendering.battle.gif_assets import (
    BattleGifLoader,
    load_gif_sequence,
)
from rendering.battle.gif_encode import encode_battle_gif
from rendering.battle.hud import BattleFonts
from rendering.battle.layout import (
    DEFAULT_GIF_FRAME_DURATION_MS,
    HEIGHT,
    OPPONENT_SPRITE_ANCHOR,
    OPPONENT_SPRITE_MAX_SIZE,
    PLAYER_SPRITE_ANCHOR,
    PLAYER_SPRITE_MAX_SIZE,
    WIDTH,
)
from rendering.battle.presentation_state import BattlePresentationState
from rendering.battle.pvp_sprite_urls import pvp_sprite_url
from rendering.battle.sprite_placement import paste_sprite

logger = logging.getLogger(__name__)


class BattlePresentationRenderer:
    """Renders engine-neutral battle state without knowing either battle engine."""

    def __init__(self, gif_loader: BattleGifLoader | None = None) -> None:
        self._assets = BattleAssets()
        self._gif_loader = gif_loader
        self._sprite_cache: dict[tuple[str, str | None, bool, bool], Image.Image] = {}
        self._missing_asset_warnings: set[tuple[str, str | None, bool, bool]] = set()

    def render_to_bytes(
        self,
        state: BattlePresentationState,
        *,
        background: Image.Image | None = None,
    ) -> bytes:
        canvas = (
            background.copy()
            if background is not None
            else self._assets.get_background().copy()
        )
        top = self._load_sprite(state.top, player_side=False)
        bottom = self._load_sprite(state.bottom, player_side=True)
        paste_sprite(
            canvas,
            top,
            anchor=OPPONENT_SPRITE_ANCHOR,
            anchor_mode="top_right",
            max_size=OPPONENT_SPRITE_MAX_SIZE,
        )
        paste_sprite(
            canvas,
            bottom,
            anchor=PLAYER_SPRITE_ANCHOR,
            anchor_mode="bottom_left",
            max_size=PLAYER_SPRITE_MAX_SIZE,
        )
        self._draw_hud(canvas, state)
        return encode_battle_gif(
            [canvas.convert("RGB")], [DEFAULT_GIF_FRAME_DURATION_MS]
        )

    def _load_sprite(self, side, *, player_side: bool) -> Image.Image:
        if side.sprite_identifier is None:
            return self._placeholder_sprite()
        key = (
            side.sprite_identifier,
            side.capture_sprite_url,
            player_side,
            side.shiny,
        )
        cached = self._sprite_cache.get(key)
        if cached is not None:
            return cached.copy()

        url = pvp_sprite_url(
            side.sprite_identifier,
            player_side=player_side,
            shiny=side.shiny,
        )
        try:
            sequence = load_gif_sequence(url, loader=self._gif_loader)
            sprite = sequence.frames[0].copy()
            self._sprite_cache[key] = sprite
            return sprite.copy()
        except Exception:
            if side.capture_sprite_url:
                try:
                    sequence = load_gif_sequence(
                        side.capture_sprite_url,
                        loader=self._gif_loader,
                    )
                    sprite = sequence.frames[0].copy()
                    self._sprite_cache[key] = sprite
                    return sprite.copy()
                except Exception:
                    pass

        if key not in self._missing_asset_warnings:
            logger.warning(
                "Missing PvP battle sprite asset identifier=%s player_side=%s shiny=%s",
                side.sprite_identifier,
                player_side,
                side.shiny,
            )
            self._missing_asset_warnings.add(key)
        sprite = self._placeholder_sprite()
        self._sprite_cache[key] = sprite
        return sprite.copy()

    @staticmethod
    def _placeholder_sprite() -> Image.Image:
        return Image.new("RGBA", (180, 180), (0, 0, 0, 0))

    def _draw_hud(self, canvas: Image.Image, state: BattlePresentationState) -> None:
        draw = ImageDraw.Draw(canvas)
        fonts = BattleFonts(
            trainer=self._assets.get_font(28),
            pokemon=self._assets.get_font(24),
            hp_text=self._assets.get_font(20),
        )
        self._draw_side(draw, state.top, x=36, y=36, align="left", fonts=fonts)
        self._draw_side(
            draw,
            state.bottom,
            x=WIDTH - 36,
            y=HEIGHT - 150,
            align="right",
            fonts=fonts,
        )
        phase = "Battle finished" if state.terminal else state.waiting_text
        turn_text = f"Turn {state.turn}"
        if phase:
            turn_text = f"{turn_text} · {phase}"
        draw.text(
            (WIDTH // 2, 28),
            _short_text(turn_text, 64),
            fill=(255, 255, 255, 255),
            font=fonts.hp_text,
            anchor="mt",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
        event = state.last_event or state.waiting_text or ""
        if event:
            draw.text(
                (WIDTH // 2, HEIGHT - 32),
                _short_text(event, 120),
                fill=(255, 255, 255, 255),
                font=fonts.hp_text,
                anchor="ms",
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255),
            )

    @staticmethod
    def _draw_side(draw, side, *, x, y, align, fonts) -> None:
        anchor = "lt" if align == "left" else "rt"
        draw.text(
            (x, y),
            _short_text(side.display_name, 24),
            fill=(255, 255, 255, 255),
            font=fonts.trainer,
            anchor=anchor,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
        pokemon_y = y + 36
        status = f" · {side.status}" if side.status else ""
        active_name = side.active_name or "Waiting for Pokémon"
        name = f"{active_name}{status}{' (KO)' if side.fainted else ''}"
        draw.text(
            (x, pokemon_y),
            _short_text(name, 28),
            fill=(255, 255, 255, 255),
            font=fonts.pokemon,
            anchor=anchor,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )
        bar_y = pokemon_y + 34
        bar_x = x if align == "left" else x - 240
        draw.rectangle(
            (bar_x, bar_y, bar_x + 240, bar_y + 16),
            fill=(80, 80, 80, 255),
            outline=(40, 40, 40, 255),
        )
        fraction = max(0.0, min(1.0, side.hp_fraction))
        if side.hp_max > 0:
            fraction = max(0.0, min(1.0, side.hp_current / side.hp_max))
        if fraction:
            draw.rectangle(
                (bar_x, bar_y, bar_x + int(240 * fraction), bar_y + 16),
                fill=(255, 204, 0, 255),
            )
        hp = f"{side.hp_current}/{side.hp_max} · {side.remaining} remaining"
        draw.text(
            (bar_x + 248 if align == "left" else bar_x - 8, bar_y - 2),
            hp,
            fill=(255, 255, 255, 255),
            font=fonts.hp_text,
            anchor="lt" if align == "left" else "rt",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255),
        )


def _short_text(value: object, limit: int) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(1, limit - 1)].rstrip()}…"
