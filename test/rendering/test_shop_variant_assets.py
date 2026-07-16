from pathlib import Path
from types import SimpleNamespace

from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    FLABEBE_COLORS,
    FURFROU_TRIMS,
    VIVILLON_PATTERNS,
)
from interfaces.discord.images import get_creature_gif

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ROOT / "showdown_variants"


def _has_asset(species: str, variant: str) -> bool:
    return (VARIANTS / species / f"{species}-{variant}.gif").is_file()


def test_all_canonical_alcremie_combinations_have_variant_assets() -> None:
    assert all(
        _has_asset("alcremie", f"{cream}-{decoration}")
        for cream in ALCREMIE_CREAMS
        for decoration in ALCREMIE_DECORATIONS
    )


def test_garden_assets_cover_only_the_confirmed_flower_colors_and_patterns() -> None:
    assert all(_has_asset("flabebe", color) for color in FLABEBE_COLORS)
    assert all(_has_asset("vivillon", pattern) for pattern in VIVILLON_PATTERNS)
    assert _has_asset("floette", "eternal")
    assert _has_asset("vivillon", "pokeball")


def test_groomer_assets_cover_all_confirmed_trims() -> None:
    assert all(_has_asset("furfrou", trim) for trim in FURFROU_TRIMS)


def test_variant_gif_resolver_uses_the_same_canonical_variant_name() -> None:
    for species, variants in (
        ("flabebe", FLABEBE_COLORS),
        ("vivillon", VIVILLON_PATTERNS),
        ("furfrou", FURFROU_TRIMS),
    ):
        for variant in variants:
            creature = SimpleNamespace(
                species=SimpleNamespace(name=species),
                current_form=SimpleNamespace(name=variant),
            )
            assert get_creature_gif(creature).endswith(
                f"/{species}/{species}-{variant}.gif"
            )


def test_natural_furfrou_uses_the_normal_species_asset() -> None:
    creature = SimpleNamespace(
        species=SimpleNamespace(pokeapi_id=676), current_form=None, is_shiny=False
    )
    assert get_creature_gif(creature).endswith("/regular/676.gif")
