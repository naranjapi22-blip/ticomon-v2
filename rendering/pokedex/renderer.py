from PIL import Image, ImageDraw

from application.pokedex.dto import PokedexEntryDTO

from .assets import PokedexAssets
from .constants import (
    CELL_HEIGHT,
    CELL_WIDTH,
    COLUMNS,
    FOOTER_HEIGHT,
    HEIGHT,
    PADDING_X,
    PADDING_Y,
    POKEMON_PER_PAGE,
    SPRITE_SIZE,
    WIDTH,
)


class PokedexRenderer:
    def __init__(self):
        self.assets = PokedexAssets()

    def _shorten_name(
        self,
        name: str,
    ) -> str:
        """
        Shortens long Pokémon names to keep the grid aligned.
        """
        if len(name) <= 10:
            return name

        return name[:9] + "…"

    def render(
        self,
        entries: tuple[PokedexEntryDTO, ...],
        page: int = 1,
    ) -> Image.Image:

        canvas = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 0),
        )

        draw = ImageDraw.Draw(canvas)

        font = self.assets.get_font(12)

        start = (page - 1) * POKEMON_PER_PAGE
        end = start + POKEMON_PER_PAGE

        page_entries = entries[start:end]

        for index, entry in enumerate(page_entries):

            row = index // COLUMNS
            column = index % COLUMNS

            cell_x = PADDING_X + column * CELL_WIDTH
            cell_y = PADDING_Y + row * CELL_HEIGHT

            if entry.discovered:
                sprite = self.assets.get_sprite(
                    entry.species.pokeapi_id,
                ).copy()
            else:
                sprite = self.assets.get_silhouette(
                    entry.species.pokeapi_id,
                ).copy()

            sprite.thumbnail(
                (
                    SPRITE_SIZE,
                    SPRITE_SIZE,
                ),
                Image.Resampling.LANCZOS,
            )

            sprite_x = cell_x + (CELL_WIDTH - sprite.width) // 2
            sprite_y = cell_y

            canvas.paste(
                sprite,
                (
                    sprite_x,
                    sprite_y,
                ),
                sprite,
            )

            name = self._shorten_name(
                entry.species.name.title(),
            )

            bbox = draw.textbbox(
                (0, 0),
                name,
                font=font,
            )

            text_width = bbox[2] - bbox[0]

            draw.text(
                (
                    cell_x + (CELL_WIDTH - text_width) // 2,
                    sprite_y + SPRITE_SIZE + 8,
                ),
                name,
                fill="white",
                font=font,
            )

        footer = f"Page {page}"

        bbox = draw.textbbox(
            (0, 0),
            footer,
            font=font,
        )

        footer_width = bbox[2] - bbox[0]

        draw.text(
            (
                (WIDTH - footer_width) // 2,
                HEIGHT - FOOTER_HEIGHT + 8,
            ),
            footer,
            fill="white",
            font=font,
        )

        return canvas
