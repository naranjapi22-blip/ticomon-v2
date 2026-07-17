from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from interfaces.discord.images import get_species_gif
from rendering.sprites import get_capture_creature_gif

BASE = "https://pub-23cb564f6c174627926c1ac0409563d4.r2.dev"


def creature(species_id, pokeapi_id, shiny=False, form=None, name="pokemon"):
    return SimpleNamespace(
        species=SimpleNamespace(
            id=species_id,
            pokeapi_id=pokeapi_id,
            name=name,
            types=("normal",),
        ),
        current_form=form,
        is_shiny=shiny,
    )


@pytest.mark.parametrize(
    ("pokeapi_id", "shiny", "suffix"),
    (
        (25, False, "/regular/25.gif"),
        (25, True, "/shiny/25.gif"),
        (906, False, "/regular/906.gif"),
        (959, False, "/regular/959.gif"),
        (1007, False, "/regular/1007.gif"),
    ),
)
def test_capture_base_gifs_use_the_historical_collection(pokeapi_id, shiny, suffix):
    assert get_capture_creature_gif(creature(pokeapi_id, pokeapi_id, shiny)).endswith(
        suffix
    )
    assert "gifs_pokeapi" not in get_capture_creature_gif(
        creature(pokeapi_id, pokeapi_id, shiny)
    )
    assert "gifs_calidad" not in get_capture_creature_gif(
        creature(pokeapi_id, pokeapi_id, shiny)
    )


def test_capture_base_source_does_not_change_general_species_source():
    assert get_species_gif(906, False) == f"{BASE}/gifs_calidad/regular/1044.gif"


def test_capture_variant_keeps_showdown_source():
    creature_value = creature(
        741,
        741,
        form=SimpleNamespace(id=336, name="pa'u"),
        name="oricorio-baile",
    )
    assert get_capture_creature_gif(creature_value) == (
        f"{BASE}/showdown_variantes/oricorio/oricorio-pau.gif"
    )


@pytest.mark.asyncio
async def test_shiny_variant_fallback_uses_historical_shiny_species_gif():
    from interfaces.discord.buttons import capture_button

    creature_value = creature(
        741,
        741,
        shiny=True,
        form=SimpleNamespace(id=336, name="pau"),
        name="oricorio-baile",
    )
    trainer = SimpleNamespace(gif="trainer.gif")
    working_animation = SimpleNamespace(gif_bytes=object())

    with (
        patch(
            "interfaces.discord.buttons.capture_button.CaptureAnimation",
            side_effect=(RuntimeError("missing"), working_animation),
        ) as animation,
        patch(
            "interfaces.discord.buttons.capture_button.asyncio.to_thread",
            new=AsyncMock(return_value=object()),
        ),
    ):
        await capture_button._capture_gif(creature_value, trainer, "POKE_BALL")

    assert animation.call_args_list[1].kwargs["sprite_path"].endswith("/shiny/741.gif")
