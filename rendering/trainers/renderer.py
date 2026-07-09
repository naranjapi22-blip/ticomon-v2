from PIL import Image, ImageDraw

from application.trainer.trainer import Trainer

from .assets import TrainerAssets
from .constants import (
    CELL_HEIGHT,
    CELL_WIDTH,
    COLUMNS,
    FOOTER_HEIGHT,
    HEIGHT,
    PADDING_X,
    PADDING_Y,
    SPRITE_SIZE,
    WIDTH,
)


class TrainerRenderer:

    def __init__(self):
        self.assets = TrainerAssets()

    def _shorten_name(
        self,
        name: str,
    ) -> str:
        replacements = {
            "Dawn (Platinum)": "Dawn Pt.",
            "Lucas (Platinum)": "Lucas Pt.",
        }

        return replacements.get(name, name)

    def render(
        self,
        trainers: list[Trainer],
        selected: Trainer,
        page: int,
    ) -> Image.Image:

        canvas = Image.new(
            "RGBA",
            (WIDTH, HEIGHT),
            (0, 0, 0, 0),
        )

        draw = ImageDraw.Draw(canvas)

        font = self.assets.get_font(16)

        for index, trainer in enumerate(trainers):

            row = index // COLUMNS
            column = index % COLUMNS

            cell_x = PADDING_X + column * CELL_WIDTH
            cell_y = PADDING_Y + row * CELL_HEIGHT

            sprite = self.assets.get_sprite(
                trainer.png,
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

            if trainer.id == selected.id:
                draw.rounded_rectangle(
                    (
                        sprite_x - 6,
                        sprite_y - 6,
                        sprite_x + sprite.width + 6,
                        sprite_y + sprite.height + 6,
                    ),
                    outline="#FFD700",
                    width=3,
                    radius=8,
                )

            canvas.paste(
                sprite,
                (
                    sprite_x,
                    sprite_y,
                ),
                sprite,
            )

            name = self._shorten_name(
                trainer.name,
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
                    sprite_y + SPRITE_SIZE + 4,
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
