"""Normalize oversized Pokemon GIFs without adding binary assets to the repo.

The script operates on local files and writes normalized copies to a separate
output directory. It intentionally has no R2 upload code or credential handling.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def normalize_frames(
    frames: list[Image.Image],
    *,
    canvas_size: int = 240,
    margin: int = 10,
) -> list[Image.Image]:
    """Return RGBA frames on a shared transparent canvas and baseline."""
    if canvas_size <= 0 or margin < 0 or margin * 2 >= canvas_size:
        raise ValueError("invalid canvas_size or margin")

    cropped: list[Image.Image | None] = []
    max_width = 1
    max_height = 1

    for frame in frames:
        rgba = frame.convert("RGBA")
        bbox = rgba.getchannel("A").getbbox()
        if bbox is None:
            cropped.append(None)
            continue
        visible = rgba.crop(bbox)
        cropped.append(visible)
        max_width = max(max_width, visible.width)
        max_height = max(max_height, visible.height)

    available = canvas_size - margin * 2
    scale = min(1.0, available / max_width, available / max_height)
    baseline = canvas_size - margin
    normalized: list[Image.Image] = []

    for visible in cropped:
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        if visible is not None:
            width = max(1, round(visible.width * scale))
            height = max(1, round(visible.height * scale))
            resized = visible.resize((width, height), Image.Resampling.LANCZOS)
            x = (canvas_size - width) // 2
            y = baseline - height
            canvas.alpha_composite(resized, (x, y))
        normalized.append(canvas)

    return normalized


def read_gif(path: Path) -> tuple[list[Image.Image], list[int], int]:
    with Image.open(path) as gif:
        frames = []
        durations = []
        for index in range(gif.n_frames):
            gif.seek(index)
            frames.append(gif.convert("RGBA"))
            durations.append(gif.info.get("duration", 100) or 100)
        loop = gif.info.get("loop", 0)
    return frames, durations, loop


def normalize_file(source: Path, destination: Path, *, margin: int = 10) -> None:
    frames, durations, loop = read_gif(source)
    normalized = normalize_frames(frames, margin=margin)
    destination.parent.mkdir(parents=True, exist_ok=True)
    normalized[0].save(
        destination,
        format="GIF",
        save_all=True,
        append_images=normalized[1:],
        duration=durations,
        loop=loop,
        disposal=2,
        optimize=False,
    )


def iter_gifs(source: Path):
    yield from source.rglob("*.gif")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--margin", type=int, default=10)
    args = parser.parse_args()

    for source in iter_gifs(args.source):
        relative = source.relative_to(args.source)
        destination = args.destination / relative
        normalize_file(source, destination, margin=args.margin)
        print(f"{source} -> {destination}")


if __name__ == "__main__":
    main()
