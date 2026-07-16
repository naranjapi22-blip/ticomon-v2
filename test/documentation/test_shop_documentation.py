from pathlib import Path

from core.shop.catalog import SHOP_PRODUCTS

ROOT = Path(__file__).resolve().parents[2]


def test_shop_documentation_mentions_all_catalog_products_and_prices():
    document = (ROOT / "docs" / "shops.md").read_text(encoding="utf-8")
    for product in SHOP_PRODUCTS:
        assert product.species_name.title() in document
        for candy_type, amount in product.cost.items():
            assert f"{amount} {candy_type.value.title()}" in document


def test_shop_documentation_matches_supported_variants_and_modes():
    document = (ROOT / "docs" / "shops.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Rotom Frost and Rotom Fan are not currently available" in document
    assert "Historical `h`, `m`," in document
    assert "`w`, and `s` aliases are not shop products." in document
    assert "are not shop products." in document
    assert "45 canonical Alcremie combinations" in document
    assert "63 combinations" not in document
    assert "Every product shows its exact GIF before confirmation" in readme
    assert "Pastry Shop is the only shop" not in readme


def test_shop_documentation_uses_the_reduced_price_schedule():
    document = (ROOT / "docs" / "shops.md").read_text(encoding="utf-8")
    assert "| Porygon | 60 Normal |" in document
    assert "| Omanyte | 60 Rock + 60 Water |" in document
    assert "| Random cream and decoration | 60 Fairy |" in document
    assert "| Selected cream, random decoration | 90 Fairy |" in document
    assert "| Selected cream and decoration | 120 Fairy |" in document
    assert "80 Normal" not in document
    assert "50 Electric + 50 Ghost" not in document
    assert "70 Electric" not in document
    assert "160 Fairy" not in document
