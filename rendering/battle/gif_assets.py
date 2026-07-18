from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

import requests
from PIL import Image, ImageSequence

from rendering.battle.layout import DEFAULT_GIF_FRAME_DURATION_MS


@dataclass(frozen=True)
class GifSequence:
    frames: tuple[Image.Image, ...]
    durations_ms: tuple[int, ...]


class BattleGifLoader(Protocol):
    def load(self, url: str) -> GifSequence: ...


_GIF_CACHE: dict[str, GifSequence] = {}
_GIF_CACHE_MAX_SIZE = 128


class RemoteBattleGifLoader:
    def load(self, url: str) -> GifSequence:
        cached = _GIF_CACHE.get(url)
        if cached is not None:
            return cached

        data = _download_bytes(url)
        sequence = _decode_gif_bytes(data)
        if len(sequence.frames) == 0:
            raise ValueError(f"GIF at {url} has no frames.")

        if len(_GIF_CACHE) >= _GIF_CACHE_MAX_SIZE:
            _GIF_CACHE.pop(next(iter(_GIF_CACHE)))
        _GIF_CACHE[url] = sequence
        return sequence


def _download_bytes(url: str) -> bytes:
    with requests.get(url, timeout=10, stream=True) as response:
        response.raise_for_status()
        return response.content


def _decode_gif_bytes(data: bytes) -> GifSequence:
    gif = Image.open(BytesIO(data))
    frames: list[Image.Image] = []
    durations_ms: list[int] = []

    for frame in ImageSequence.Iterator(gif):
        rgba = frame.convert("RGBA")
        frames.append(rgba)
        duration = frame.info.get("duration", DEFAULT_GIF_FRAME_DURATION_MS)
        if not duration or duration <= 0:
            duration = DEFAULT_GIF_FRAME_DURATION_MS
        durations_ms.append(int(duration))

    if not frames:
        frames.append(gif.convert("RGBA"))
        durations_ms.append(DEFAULT_GIF_FRAME_DURATION_MS)

    return GifSequence(
        frames=tuple(frames),
        durations_ms=tuple(durations_ms),
    )


def load_gif_sequence(url: str, loader: BattleGifLoader | None = None) -> GifSequence:
    gif_loader = loader or RemoteBattleGifLoader()
    candidates = [url] if url.endswith(".gif") else [f"{url}.gif", url]
    last_error: Exception | None = None

    for candidate in candidates:
        try:
            return gif_loader.load(candidate)
        except (requests.HTTPError, OSError, ValueError) as error:
            last_error = error

    if last_error is not None:
        raise last_error
    raise ValueError(f"Could not load GIF from {url}")
