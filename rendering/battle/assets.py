from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

from rendering.safari.assets import SafariAssets

WIDTH = 1020
HEIGHT = 574


class BattleAssets:
    def __init__(self) -> None:
        self._safari_assets = SafariAssets()
        backgrounds_root = Path(__file__).resolve().parents[1] / "assets"
        self._backgrounds_root = backgrounds_root / "backgrounds"

    @lru_cache(maxsize=1)
    def get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return self._safari_assets.get_font(size)

    def get_sprite(self, pokeapi_id: int, *, shiny: bool = False) -> Image.Image:
        return self._safari_assets.get_sprite(
            pokeapi_id,
            shiny=shiny,
        )

    def get_background(self) -> Image.Image:
        return self.get_background_for_battle(0)

    @lru_cache(maxsize=64)
    def get_background_for_battle(self, battle_id: int) -> Image.Image:
        backgrounds = sorted(self._backgrounds_root.glob("*.png"))
        if not backgrounds:
            return Image.new("RGBA", (WIDTH, HEIGHT), (40, 80, 40, 255))

        background_path = backgrounds[battle_id % len(backgrounds)]
        background = Image.open(background_path).convert("RGBA")
        return background.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
