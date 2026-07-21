from __future__ import annotations

from PIL import Image

from rendering.battle.gif_assets import GifSequence
from rendering.battle.presentation_renderer import BattlePresentationRenderer
from rendering.battle.presentation_state import (
    BattlePresentationSide,
    BattlePresentationState,
)
from rendering.battle.pvp_sprite_urls import pvp_sprite_url, showdown_sprite_identifier


class RecordingLoader:
    def __init__(self, *, fail: set[str] | None = None) -> None:
        self.urls: list[str] = []
        self.fail = fail or set()

    def load(self, url: str) -> GifSequence:
        self.urls.append(url)
        if url in self.fail:
            raise OSError("missing")
        return GifSequence(
            frames=(Image.new("RGBA", (64, 64), (20, 80, 160, 255)),),
            durations_ms=(100,),
        )


def _side(name: str, identifier: str, *, shiny: bool = False):
    return BattlePresentationSide(
        trainer_id=1,
        display_name=name,
        active_name=identifier,
        sprite_identifier=identifier,
        shiny=shiny,
        hp_current=50,
        hp_max=100,
        hp_fraction=0.5,
        status="PAR" if shiny else None,
        fainted=False,
        remaining=3,
    )


def test_pvp_sprite_urls_use_showdown_identifiers_and_orientation():
    assert showdown_sprite_identifier("Oricorio", "Pa'u") == "oricorio-pau"
    assert pvp_sprite_url("pikachu", player_side=False, shiny=False).endswith(
        "/PVP/regular/pikachu.gif"
    )
    assert pvp_sprite_url("pikachu", player_side=True, shiny=False).endswith(
        "/PVP/back/pikachu.gif"
    )
    assert pvp_sprite_url("charizard-mega-x", player_side=False, shiny=True).endswith(
        "/PVP/shiny/charizard-mega-x.gif"
    )
    assert pvp_sprite_url("charizard-mega-x", player_side=True, shiny=True).endswith(
        "/PVP/back_shiny/charizard-mega-x.gif"
    )


def test_presentation_renderer_uses_front_and_back_sprites():
    loader = RecordingLoader()
    renderer = BattlePresentationRenderer(gif_loader=loader)
    state = BattlePresentationState(
        top=_side("Rival", "pikachu"),
        bottom=_side("Player", "charizard", shiny=True),
        turn=2,
        last_event="Charizard used Flamethrower.",
    )

    result = renderer.render_to_bytes(state)

    assert result.startswith(b"GIF")
    assert any(url.endswith("/PVP/regular/pikachu.gif") for url in loader.urls)
    assert any(url.endswith("/PVP/back_shiny/charizard.gif") for url in loader.urls)


def test_presentation_renderer_falls_back_when_sprite_is_missing():
    missing_url = pvp_sprite_url("missingno", player_side=False, shiny=False)
    loader = RecordingLoader(fail={missing_url})
    renderer = BattlePresentationRenderer(gif_loader=loader)
    state = BattlePresentationState(
        top=_side("Rival", "missingno"),
        bottom=_side("Player", "pikachu"),
        turn=1,
        last_event="Waiting for an action.",
    )

    result = renderer.render_to_bytes(state)

    assert result.startswith(b"GIF")
