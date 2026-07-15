from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from rendering.spawn_preview import generate_silhouette, generate_spawn_preview


def test_spawn_preview_places_silhouettes_on_neutral_panel():
    preview = generate_spawn_preview(
        [SimpleNamespace(species=SimpleNamespace(pokeapi_id=25))]
    )
    image = Image.open(BytesIO(preview.getvalue())).convert("RGBA")

    assert image.size == (128, 128)
    assert image.getpixel((0, 0)) == (224, 224, 224, 255)
    assert image.getcolors(maxcolors=100_000)
    assert (0, 0, 0, 255) in image.getdata()


def test_silhouette_keeps_sprite_proportions_and_opaque_shape():
    sprite = Image.new("RGBA", (16, 16), (255, 255, 255, 0))
    sprite.putpixel((8, 8), (255, 255, 255, 128))

    silhouette = generate_silhouette(sprite)

    assert silhouette.size == sprite.size
    assert silhouette.getpixel((8, 8)) == (0, 0, 0, 255)
    assert silhouette.getpixel((0, 0)) == (255, 255, 255, 0)
