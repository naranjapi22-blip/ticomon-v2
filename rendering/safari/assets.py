from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

from core.safari.domain import SafariMap

ROOT = Path(__file__).resolve().parents[1]
FONTS_ROOT = ROOT / "assets" / "fonts"
FONDOS_ROOT = ROOT / "assets" / "fondos"
REGULAR_ROOT = ROOT / "assets" / "regular"
SHINY_ROOT = ROOT / "assets" / "shiny"

BACKGROUND_BY_MAP: dict[SafariMap, str] = {
    SafariMap.FOREST: "grass.png",
    SafariMap.MOUNTAIN: "rock.png",
    SafariMap.COAST: "water.png",
    SafariMap.SWAMP: "poison.png",
    SafariMap.PLAINS: "normal.png",
}


class SafariAssets:
    @lru_cache(maxsize=8)
    def get_font(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(FONTS_ROOT / "DejaVuSans-Bold.ttf", size)

    @lru_cache(maxsize=32)
    def get_background(self, safari_map: SafariMap) -> Image.Image:
        filename = BACKGROUND_BY_MAP.get(safari_map, "safari.png")
        path = FONDOS_ROOT / filename
        if not path.exists():
            path = FONDOS_ROOT / "safari.png"
        return Image.open(path).convert("RGBA")

    @lru_cache(maxsize=2048)
    def get_sprite(self, species_id: int, shiny: bool) -> Image.Image:
        path = (SHINY_ROOT if shiny else REGULAR_ROOT) / f"{species_id}.png"
        if not path.exists():
            path = REGULAR_ROOT / f"{species_id}.png"
        return Image.open(path).convert("RGBA")
