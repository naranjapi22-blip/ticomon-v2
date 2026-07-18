from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from rendering.battle.assets import BattleAssets
from rendering.battle.frame_state import BattleFrameState
from rendering.battle.gif_assets import BattleGifLoader, GifSequence, load_gif_sequence
from rendering.battle.gif_encode import encode_battle_gif, subsample_frame_indices
from rendering.battle.hud import BattleFonts, draw_battle_hud
from rendering.battle.layout import (
    DEFAULT_GIF_FRAME_DURATION_MS,
    MAX_BATTLE_GIF_FRAMES,
    OPPONENT_SPRITE_ANCHOR,
    OPPONENT_SPRITE_MAX_SIZE,
    PLAYER_SPRITE_ANCHOR,
    PLAYER_SPRITE_MAX_SIZE,
)
from rendering.battle.sprite_placement import paste_sprite
from rendering.battle.sprite_urls import (
    battle_initiator_sprite_url,
    battle_opponent_sprite_url,
)


class BattleRenderer:
    def __init__(self, gif_loader: BattleGifLoader | None = None) -> None:
        self._assets = BattleAssets()
        self._gif_loader = gif_loader

    def get_background_for_battle(self, battle_id: int) -> Image.Image:
        return self._assets.get_background_for_battle(battle_id)

    def render(
        self,
        frame: BattleFrameState,
        *,
        background: Image.Image | None = None,
    ) -> Image.Image:
        gif_bytes = self.render_to_bytes(frame, background=background)
        gif = Image.open(BytesIO(gif_bytes))
        gif.seek(0)
        return gif.convert("RGBA")

    def render_to_bytes(
        self,
        frame: BattleFrameState,
        *,
        background: Image.Image | None = None,
    ) -> bytes:
        base_background = (
            background.copy()
            if background is not None
            else self._assets.get_background().copy()
        )
        opponent_sequence = self._load_sprite_sequence(
            battle_opponent_sprite_url(
                frame.side_b_pokeapi_id,
                shiny=frame.side_b_shiny,
            ),
            pokeapi_id=frame.side_b_pokeapi_id,
            shiny=frame.side_b_shiny,
        )
        initiator_sequence = self._load_sprite_sequence(
            battle_initiator_sprite_url(
                frame.side_a_pokeapi_id,
                shiny=frame.side_a_shiny,
            ),
            pokeapi_id=frame.side_a_pokeapi_id,
            shiny=frame.side_a_shiny,
        )

        fonts = BattleFonts(
            trainer=self._assets.get_font(28),
            pokemon=self._assets.get_font(24),
            hp_text=self._assets.get_font(20),
        )
        frames, durations = self._compose_frames(
            frame,
            base_background=base_background,
            opponent_sequence=opponent_sequence,
            initiator_sequence=initiator_sequence,
            fonts=fonts,
        )

        return encode_battle_gif(frames, durations)

    def _compose_frames(
        self,
        frame: BattleFrameState,
        *,
        base_background: Image.Image,
        opponent_sequence: GifSequence,
        initiator_sequence: GifSequence,
        fonts: BattleFonts,
    ) -> tuple[list[Image.Image], list[int]]:
        source_frame_count = max(
            len(opponent_sequence.frames),
            len(initiator_sequence.frames),
        )
        frame_indices = subsample_frame_indices(
            source_frame_count,
            MAX_BATTLE_GIF_FRAMES,
        )
        output_frames: list[Image.Image] = []
        durations: list[int] = []

        for source_index in frame_indices:
            canvas = base_background.copy()
            opponent_frame = opponent_sequence.frames[
                source_index % len(opponent_sequence.frames)
            ]
            initiator_frame = initiator_sequence.frames[
                source_index % len(initiator_sequence.frames)
            ]

            paste_sprite(
                canvas,
                opponent_frame,
                anchor=OPPONENT_SPRITE_ANCHOR,
                anchor_mode="top_right",
                max_size=OPPONENT_SPRITE_MAX_SIZE,
            )
            paste_sprite(
                canvas,
                initiator_frame,
                anchor=PLAYER_SPRITE_ANCHOR,
                anchor_mode="bottom_left",
                max_size=PLAYER_SPRITE_MAX_SIZE,
            )

            draw = ImageDraw.Draw(canvas)
            draw_battle_hud(draw, frame, fonts)

            opponent_duration = opponent_sequence.durations_ms[
                source_index % len(opponent_sequence.durations_ms)
            ]
            initiator_duration = initiator_sequence.durations_ms[
                source_index % len(initiator_sequence.durations_ms)
            ]
            durations.append(
                max(
                    opponent_duration,
                    initiator_duration,
                    DEFAULT_GIF_FRAME_DURATION_MS,
                )
            )
            output_frames.append(canvas.convert("RGB"))

        return output_frames, durations

    def _load_sprite_sequence(
        self,
        url: str,
        *,
        pokeapi_id: int,
        shiny: bool,
    ) -> GifSequence:
        try:
            return load_gif_sequence(url, loader=self._gif_loader)
        except Exception:
            sprite = self._assets.get_sprite(pokeapi_id, shiny=shiny).convert("RGBA")
            return GifSequence(
                frames=(sprite,),
                durations_ms=(DEFAULT_GIF_FRAME_DURATION_MS,),
            )
