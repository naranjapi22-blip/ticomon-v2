from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parent.parent

REGULAR_ROOT = ROOT / "assets" / "regular"
FONTS_ROOT = ROOT / "assets" / "fonts"


class PokedexAssets:
    """
    Loads and caches Pokédex assets.
    """

    def _trim(
        self,
        image: Image.Image,
    ) -> Image.Image:
        """
        Removes transparent borders from a sprite.
        """

        bbox = image.getbbox()

        if bbox is None:
            return image

        return image.crop(bbox)

    @lru_cache(maxsize=2048)
    def get_sprite(
        self,
        species_id: int,
    ) -> Image.Image:

        path = REGULAR_ROOT / f"{species_id}.png"

        return Image.open(path).convert("RGBA")

    @lru_cache(maxsize=2048)
    def get_silhouette(
        self,
        species_id: int,
    ) -> Image.Image:

        sprite = self.get_sprite(species_id).copy()

        alpha = sprite.getchannel("A")

        silhouette = Image.new(
            "RGBA",
            sprite.size,
            (30, 30, 30, 255),
        )

        silhouette.putalpha(alpha)

        return silhouette

    @lru_cache(maxsize=8)
    def get_font(
        self,
        size: int,
    ) -> ImageFont.FreeTypeFont:

        return ImageFont.truetype(
            FONTS_ROOT / "pokemon-font.ttf",
            size,
        )
