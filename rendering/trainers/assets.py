from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

ASSETS_PATH = Path(__file__).resolve().parents[1] / "assets"

TRAINERS_PATH = ASSETS_PATH / "trainers"

FONTS_PATH = ASSETS_PATH / "fonts"

FONT_PATH = FONTS_PATH / "pokemon-font.ttf"


class TrainerAssets:
    @lru_cache(maxsize=64)
    def get_sprite(
        self,
        filename: str,
    ) -> Image.Image:
        return Image.open(
            TRAINERS_PATH / filename,
        ).convert("RGBA")

    @lru_cache(maxsize=8)
    def get_font(
        self,
        size: int,
    ) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(
            str(FONT_PATH),
            size,
        )
