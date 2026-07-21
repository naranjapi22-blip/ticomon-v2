from __future__ import annotations

import logging

import pytest
from PIL import Image

from rendering.battle.gif_assets import GifSequence
from rendering.battle.presentation_renderer import BattlePresentationRenderer
from rendering.battle.presentation_state import (
    BattlePresentationSide,
    BattlePresentationState,
)
from rendering.battle.pvp_sprite_urls import pvp_sprite_url, showdown_sprite_identifier
from rendering.sprites import get_capture_species_gif


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


def _side(
    name: str,
    identifier: str,
    *,
    shiny: bool = False,
    capture_sprite_url: str | None = None,
):
    return BattlePresentationSide(
        trainer_id=1,
        display_name=name,
        active_name=identifier,
        sprite_identifier=identifier,
        capture_sprite_url=capture_sprite_url,
        shiny=shiny,
        hp_current=50,
        hp_max=100,
        hp_fraction=0.5,
        status="PAR" if shiny else None,
        fainted=False,
        remaining=3,
    )


def _empty_side(name: str):
    return BattlePresentationSide(
        trainer_id=1,
        display_name=name,
        active_name=None,
        sprite_identifier=None,
        shiny=False,
        hp_current=0,
        hp_max=1,
        hp_fraction=0.0,
        status=None,
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


def test_compound_showdown_names_use_asset_filename_slugs():
    names = {
        "Iron Crown": "iron-crown",
        "Iron Boulder": "iron-boulder",
        "Iron Hands": "iron-hands",
        "Iron Leaves": "iron-leaves",
        "Iron Moth": "iron-moth",
        "Iron Thorns": "iron-thorns",
        "Iron Treads": "iron-treads",
        "Iron Valiant": "iron-valiant",
        "Walking Wake": "walking-wake",
        "Great Tusk": "great-tusk",
        "Roaring Moon": "roaring-moon",
        "Flutter Mane": "flutter-mane",
        "Scream Tail": "scream-tail",
        "Slither Wing": "slither-wing",
        "Sandy Shocks": "sandy-shocks",
        "Brute Bonnet": "brute-bonnet",
        "Gouging Fire": "gouging-fire",
        "Raging Bolt": "raging-bolt",
    }
    from rendering.battle.pvp_sprite_urls import showdown_sprite_identifier

    assert {showdown_sprite_identifier(name) for name in names} == set(names.values())


def test_legacy_and_form_names_remain_normalized():
    from rendering.battle.pvp_sprite_urls import showdown_sprite_identifier

    assert showdown_sprite_identifier("Mr. Mime") == "mr-mime"
    assert showdown_sprite_identifier("Mime Jr.") == "mime-jr"
    assert showdown_sprite_identifier("Type: Null") == "type-null"
    assert showdown_sprite_identifier("Tapu Koko") == "tapu-koko"
    assert showdown_sprite_identifier("Ho-Oh") == "ho-oh"
    assert showdown_sprite_identifier("Porygon-Z") == "porygon-z"
    assert showdown_sprite_identifier("Nidoran-F") == "nidoran-f"
    assert showdown_sprite_identifier("Nidoran-M") == "nidoran-m"
    assert showdown_sprite_identifier("Oricorio-Pa'u") == "oricorio-pau"


def test_empty_side_does_not_load_or_warn(caplog):
    caplog.set_level(logging.WARNING, logger="rendering.battle.presentation_renderer")
    loader = RecordingLoader(
        fail={pvp_sprite_url("notarealspecies", player_side=False, shiny=False)}
    )
    renderer = BattlePresentationRenderer(gif_loader=loader)
    state = BattlePresentationState(
        top=_empty_side("Rival"),
        bottom=_empty_side("Player"),
        turn=0,
        last_event="Waiting for players...",
    )

    renderer.render_to_bytes(state)

    assert loader.urls == []
    assert "Missing PvP battle sprite asset" not in caplog.text


def test_missing_asset_is_cached_and_warned_once(caplog):
    caplog.set_level(logging.WARNING, logger="rendering.battle.presentation_renderer")
    loader = RecordingLoader(
        fail={pvp_sprite_url("notarealspecies", player_side=False, shiny=False)}
    )
    renderer = BattlePresentationRenderer(gif_loader=loader)
    state = BattlePresentationState(
        top=_side("Rival", "notarealspecies"),
        bottom=_empty_side("Player"),
        turn=1,
        last_event="Waiting for an action.",
    )

    renderer.render_to_bytes(state)
    renderer.render_to_bytes(state)

    assert len(loader.urls) == 1
    assert caplog.text.count("Missing PvP battle sprite asset") == 1


@pytest.mark.parametrize("folder", ["regular", "back", "shiny", "back_shiny"])
def test_iron_hands_missing_pvp_asset_uses_capture_gif(folder, caplog):
    caplog.set_level(logging.WARNING, logger="rendering.battle.presentation_renderer")
    url = pvp_sprite_url(
        "iron-hands",
        player_side=folder in {"back", "back_shiny"},
        shiny=folder in {"shiny", "back_shiny"},
    )
    capture_url = get_capture_species_gif(992, folder in {"shiny", "back_shiny"})
    loader = RecordingLoader(fail={url})
    renderer = BattlePresentationRenderer(gif_loader=loader)

    sprite_side = _side(
        "Rival" if folder not in {"back", "back_shiny"} else "Player",
        "iron-hands",
        shiny=folder in {"shiny", "back_shiny"},
        capture_sprite_url=capture_url,
    )
    renderer.render_to_bytes(
        BattlePresentationState(
            top=sprite_side if folder in {"regular", "shiny"} else _empty_side("Rival"),
            bottom=(
                sprite_side
                if folder in {"back", "back_shiny"}
                else _empty_side("Player")
            ),
            turn=1,
            last_event="Iron Hands appeared.",
        )
    )

    assert loader.urls == [url, capture_url]
    assert "Missing PvP battle sprite asset identifier=iron-hands" not in caplog.text


def test_exact_pvp_sprite_has_priority_over_capture_gif():
    capture_url = get_capture_species_gif(992, False)
    pvp_url = pvp_sprite_url("iron-hands", player_side=False, shiny=False)
    loader = RecordingLoader()
    renderer = BattlePresentationRenderer(gif_loader=loader)

    renderer.render_to_bytes(
        BattlePresentationState(
            top=_side(
                "Rival",
                "iron-hands",
                capture_sprite_url=capture_url,
            ),
            bottom=_empty_side("Player"),
            turn=1,
            last_event="Iron Hands appeared.",
        )
    )

    assert loader.urls == [pvp_url]


def test_missing_pvp_and_capture_assets_show_unavailable(caplog):
    caplog.set_level(logging.WARNING, logger="rendering.battle.presentation_renderer")
    pvp_url = pvp_sprite_url("iron-hands", player_side=False, shiny=False)
    capture_url = get_capture_species_gif(992, False)
    loader = RecordingLoader(fail={pvp_url, capture_url})
    renderer = BattlePresentationRenderer(gif_loader=loader)

    renderer.render_to_bytes(
        BattlePresentationState(
            top=_side(
                "Rival",
                "iron-hands",
                capture_sprite_url=capture_url,
            ),
            bottom=_empty_side("Player"),
            turn=1,
            last_event="Iron Hands appeared.",
        )
    )

    assert loader.urls == [pvp_url, capture_url]
    assert "Missing PvP battle sprite asset identifier=iron-hands" in caplog.text


def test_empty_side_can_transition_to_real_sprite():
    loader = RecordingLoader()
    renderer = BattlePresentationRenderer(gif_loader=loader)
    empty = BattlePresentationState(
        top=_empty_side("Rival"),
        bottom=_empty_side("Player"),
        turn=0,
        last_event="Waiting for players...",
    )
    active = BattlePresentationState(
        top=_side("Rival", "iron-crown"),
        bottom=_empty_side("Player"),
        turn=1,
        last_event="Rival sent out Iron Crown.",
    )

    renderer.render_to_bytes(empty)
    renderer.render_to_bytes(active)

    assert any(url.endswith("/PVP/regular/iron-crown.gif") for url in loader.urls)


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
    missing_url = pvp_sprite_url("notarealspecies", player_side=False, shiny=False)
    loader = RecordingLoader(fail={missing_url})
    renderer = BattlePresentationRenderer(gif_loader=loader)
    state = BattlePresentationState(
        top=_side("Rival", "notarealspecies"),
        bottom=_side("Player", "pikachu"),
        turn=1,
        last_event="Waiting for an action.",
    )

    result = renderer.render_to_bytes(state)

    assert result.startswith(b"GIF")
