from __future__ import annotations

from typing import Literal

from PIL import Image


def scale_sprite(sprite: Image.Image, max_size: int) -> Image.Image:
    scale = min(max_size / sprite.width, max_size / sprite.height)
    if scale <= 0:
        return sprite
    new_width = max(int(sprite.width * scale), 1)
    new_height = max(int(sprite.height * scale), 1)
    if new_width == sprite.width and new_height == sprite.height:
        return sprite
    return sprite.resize((new_width, new_height), Image.Resampling.LANCZOS)


def paste_sprite(
    canvas: Image.Image,
    sprite: Image.Image,
    *,
    anchor: tuple[int, int],
    anchor_mode: Literal["bottom_left", "top_right"],
    max_size: int,
    flip: bool = False,
) -> None:
    scaled = scale_sprite(sprite.copy(), max_size)
    if flip:
        scaled = scaled.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    content_bbox = scaled.getbbox()
    if content_bbox is None:
        return

    content_left, content_top, content_right, content_bottom = content_bbox
    anchor_x, anchor_y = anchor
    if anchor_mode == "bottom_left":
        position = (anchor_x - content_left, anchor_y - content_bottom)
    else:
        position = (anchor_x - content_right, anchor_y - content_top)

    canvas.paste(scaled, position, scaled)
