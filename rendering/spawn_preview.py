import io
from pathlib import Path

from PIL import Image

SPRITE_SIZE = 128
SPACING = 10


def generate_silhouette(
    image: Image.Image,
) -> Image.Image:
    """
    Converts a sprite into a solid black silhouette.
    """

    image = image.copy()

    pixels = image.load()

    for y in range(image.height):
        for x in range(image.width):
            _, _, _, alpha = pixels[x, y]

            if alpha > 0:
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

    return image


def generate_spawn_preview(
    opportunities,
) -> io.BytesIO:
    sprites = []

    assets_path = Path(__file__).parent / "assets" / "regular"

    for opportunity in opportunities:
        sprite = Image.open(assets_path / f"{opportunity.species.id}.png").convert(
            "RGBA"
        )

        sprite = generate_silhouette(
            sprite,
        )

        sprite = sprite.resize(
            (SPRITE_SIZE, SPRITE_SIZE),
            Image.Resampling.NEAREST,
        )

        sprites.append(
            sprite,
        )

    width = SPRITE_SIZE * len(sprites) + SPACING * (len(sprites) - 1)

    canvas = Image.new(
        "RGBA",
        (width, SPRITE_SIZE),
        (0, 0, 0, 0),
    )

    x = 0

    for sprite in sprites:
        canvas.paste(
            sprite,
            (x, 0),
            sprite,
        )

        x += SPRITE_SIZE + SPACING

    buffer = io.BytesIO()

    canvas.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return buffer
