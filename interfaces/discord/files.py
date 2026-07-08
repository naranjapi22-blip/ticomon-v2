from io import BytesIO

import discord
from PIL import Image


def image_to_discord_file(
    image: Image.Image,
    filename: str = "image.png",
) -> discord.File:
    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return discord.File(
        buffer,
        filename=filename,
    )
