from __future__ import annotations

from io import BytesIO

from PIL import Image

from rendering.battle.layout import (
    BATTLE_GIF_OUTPUT_SCALE,
    BATTLE_GIF_PALETTE_COLORS,
    DISCORD_MAX_GIF_BYTES,
    HEIGHT,
    MAX_BATTLE_GIF_FRAMES,
    WIDTH,
)


def subsample_frame_indices(source_count: int, max_frames: int) -> list[int]:
    if source_count <= 0:
        return [0]
    if source_count <= max_frames:
        return list(range(source_count))
    return [int(index * source_count / max_frames) for index in range(max_frames)]


def encode_battle_gif(
    frames: list[Image.Image],
    durations_ms: list[int],
) -> bytes:
    scale = BATTLE_GIF_OUTPUT_SCALE
    palette_colors = BATTLE_GIF_PALETTE_COLORS
    max_frames = min(len(frames), MAX_BATTLE_GIF_FRAMES)

    while True:
        selected_indices = subsample_frame_indices(len(frames), max_frames)
        selected_frames = [frames[index] for index in selected_indices]
        selected_durations = [durations_ms[index] for index in selected_indices]
        encoded = _encode_at_quality(
            selected_frames,
            selected_durations,
            scale=scale,
            palette_colors=palette_colors,
        )
        if len(encoded) <= DISCORD_MAX_GIF_BYTES or scale <= 0.45:
            return encoded

        scale -= 0.07
        max_frames = max(12, max_frames - 4)
        palette_colors = max(64, palette_colors - 16)


def _encode_at_quality(
    frames: list[Image.Image],
    durations_ms: list[int],
    *,
    scale: float,
    palette_colors: int,
) -> bytes:
    output_size = (
        max(1, int(WIDTH * scale)),
        max(1, int(HEIGHT * scale)),
    )
    palette_frames = [
        frame.resize(output_size, Image.Resampling.LANCZOS).quantize(
            colors=palette_colors,
            method=Image.Quantize.MEDIANCUT,
        )
        for frame in frames
    ]

    buffer = BytesIO()
    palette_frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=palette_frames[1:],
        duration=durations_ms,
        loop=0,
        disposal=2,
        optimize=True,
    )
    return buffer.getvalue()
