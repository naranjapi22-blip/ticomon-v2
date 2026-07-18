from io import BytesIO

from PIL import Image

from rendering.battle.sprite_urls import (
    battle_initiator_sprite_url,
    battle_opponent_sprite_url,
)
from rendering.gif_urls import BASE_GIF_URL


def test_battle_initiator_sprite_urls():
    assert battle_initiator_sprite_url(25, shiny=False) == f"{BASE_GIF_URL}/back/25"
    assert (
        battle_initiator_sprite_url(25, shiny=True) == f"{BASE_GIF_URL}/back_shiny/25"
    )


def test_battle_opponent_sprite_urls():
    assert battle_opponent_sprite_url(7, shiny=False) == f"{BASE_GIF_URL}/regular/7"
    assert battle_opponent_sprite_url(7, shiny=True) == f"{BASE_GIF_URL}/shiny/7"


def _make_test_gif(color: tuple[int, int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (96, 96), color).save(
        buffer,
        format="GIF",
        save_all=True,
        duration=100,
        loop=0,
    )
    return buffer.getvalue()
