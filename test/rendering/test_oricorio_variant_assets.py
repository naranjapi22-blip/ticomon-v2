from pathlib import Path
from types import SimpleNamespace

import pytest

from interfaces.discord.images import get_creature_gif, get_opportunity_gif
from rendering.sprites import get_capture_sprite
from rendering.variant_assets import get_variant_asset_key

ROOT = Path(__file__).resolve().parents[2]


def _variant_creature(variant_id: int, variant_name: str):
    return SimpleNamespace(
        species=SimpleNamespace(
            id=741,
            name="oricorio-baile",
            pokeapi_id=741,
        ),
        current_form=SimpleNamespace(id=variant_id, name=variant_name),
        is_shiny=False,
    )


@pytest.mark.parametrize(
    ("variant_id", "variant_name"),
    (
        (336, "pau"),
        (337, "pompom"),
        (338, "sensu"),
    ),
)
def test_oricorio_variant_gifs_use_the_canonical_oricorio_asset_key(
    variant_id: int,
    variant_name: str,
) -> None:
    creature = _variant_creature(variant_id, variant_name)
    opportunity = SimpleNamespace(
        species=creature.species,
        initial_form=creature.current_form,
        is_shiny=False,
    )
    expected_suffix = f"/oricorio/oricorio-{variant_name}.gif"

    assert get_creature_gif(creature).endswith(expected_suffix)
    assert get_opportunity_gif(opportunity).endswith(expected_suffix)
    assert get_capture_sprite(creature).endswith(expected_suffix)
    assert (
        ROOT / "showdown_variants" / "oricorio" / f"oricorio-{variant_name}.gif"
    ).is_file()


def test_oricorio_pau_asset_key_accepts_the_semantic_apostrophe() -> None:
    assert get_variant_asset_key("oricorio-baile", "pa'u") == ("oricorio", "pau")
    assert get_variant_asset_key("oricorio-baile", "pa’u") == ("oricorio", "pau")


def test_oricorio_baile_base_form_uses_the_species_gif() -> None:
    creature = SimpleNamespace(
        species=SimpleNamespace(id=741, name="oricorio-baile", pokeapi_id=741),
        current_form=None,
        is_shiny=False,
    )
    opportunity = SimpleNamespace(
        species=creature.species,
        initial_form=None,
        is_shiny=False,
    )

    assert get_creature_gif(creature).endswith("/regular/741.gif")
    assert get_opportunity_gif(opportunity).endswith("/regular/741.gif")
    assert get_capture_sprite(creature).endswith("/regular/741.gif")
