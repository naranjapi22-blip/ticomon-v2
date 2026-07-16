from core.candy.candy_type import CandyType
from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    FLABEBE_COLORS,
    FURFROU_TRIMS,
    SHOP_PRODUCTS,
    VIVILLON_PATTERNS,
    ShopStore,
    alcremie_cost,
    alcremie_variant_name,
)


def test_catalog_contains_only_confirmed_rotom_forms() -> None:
    rotom = [product for product in SHOP_PRODUCTS if product.species_name == "rotom"]
    assert [product.id for product in rotom] == [
        "rotom",
        "rotom_heat",
        "rotom_wash",
        "rotom_mow",
    ]
    assert [product.variant_name for product in rotom] == [None, "heat", "wash", "mow"]


def test_fossil_prices_are_fixed_by_category() -> None:
    prices = {product.id: dict(product.cost.items()) for product in SHOP_PRODUCTS}
    assert prices["cranidos"] == {CandyType.ROCK: 120}
    assert prices["omanyte"] == {CandyType.ROCK: 60, CandyType.WATER: 60}
    assert prices["dracozolt"] == {CandyType.ELECTRIC: 90, CandyType.DRAGON: 90}


def test_all_shop_prices_match_the_current_schedule() -> None:
    prices = {
        product.id: dict(product.cost.items())
        for product in SHOP_PRODUCTS
        if product.store in (ShopStore.TECHNOLOGY, ShopStore.FOSSIL)
    }
    assert prices == {
        "porygon": {CandyType.NORMAL: 60},
        "rotom": {CandyType.ELECTRIC: 40, CandyType.GHOST: 40},
        "rotom_heat": {CandyType.ELECTRIC: 55, CandyType.FIRE: 55},
        "rotom_wash": {CandyType.ELECTRIC: 55, CandyType.WATER: 55},
        "rotom_mow": {CandyType.ELECTRIC: 55, CandyType.GRASS: 55},
        "golett": {CandyType.GROUND: 45, CandyType.GHOST: 45},
        "omanyte": {CandyType.ROCK: 60, CandyType.WATER: 60},
        "kabuto": {CandyType.ROCK: 60, CandyType.WATER: 60},
        "aerodactyl": {CandyType.ROCK: 60, CandyType.FLYING: 60},
        "lileep": {CandyType.ROCK: 60, CandyType.GRASS: 60},
        "anorith": {CandyType.ROCK: 60, CandyType.BUG: 60},
        "cranidos": {CandyType.ROCK: 120},
        "shieldon": {CandyType.ROCK: 60, CandyType.STEEL: 60},
        "tirtouga": {CandyType.WATER: 60, CandyType.ROCK: 60},
        "archen": {CandyType.ROCK: 60, CandyType.FLYING: 60},
        "tyrunt": {CandyType.ROCK: 75, CandyType.DRAGON: 75},
        "amaura": {CandyType.ROCK: 75, CandyType.ICE: 75},
        "dracozolt": {CandyType.ELECTRIC: 90, CandyType.DRAGON: 90},
        "arctozolt": {CandyType.ELECTRIC: 90, CandyType.ICE: 90},
        "dracovish": {CandyType.WATER: 90, CandyType.DRAGON: 90},
        "arctovish": {CandyType.WATER: 90, CandyType.ICE: 90},
    }


def test_alcremie_catalog_has_45_canonical_combinations() -> None:
    combinations = {
        alcremie_variant_name(cream, decoration)
        for cream in ALCREMIE_CREAMS
        for decoration in ALCREMIE_DECORATIONS
    }
    assert len(ALCREMIE_CREAMS) == 9
    assert len(ALCREMIE_DECORATIONS) == 5
    assert len(combinations) == 45
    assert alcremie_cost("random").get(CandyType.FAIRY) == 60
    assert alcremie_cost("cream").get(CandyType.FAIRY) == 90
    assert alcremie_cost("custom").get(CandyType.FAIRY) == 120


def test_garden_products_use_only_confirmed_normal_variants() -> None:
    products = {product.id: product for product in SHOP_PRODUCTS}
    flabebe = [
        product for product in SHOP_PRODUCTS if product.species_name == "flabebe"
    ]

    assert [product.variant_name for product in flabebe] == list(FLABEBE_COLORS)
    assert all(product.cost.get(CandyType.FAIRY) == 45 for product in flabebe)
    assert products["vivillon_random"].random_variant_names == VIVILLON_PATTERNS
    assert products["vivillon_random"].cost.get(CandyType.BUG) == 35
    assert products["vivillon_random"].cost.get(CandyType.FLYING) == 35
    assert all(
        products[f"vivillon_{pattern}"].cost.get(CandyType.BUG) == 50
        and products[f"vivillon_{pattern}"].cost.get(CandyType.FLYING) == 50
        for pattern in VIVILLON_PATTERNS
    )
    assert "vivillon_pokeball" not in products
    assert not any(product.variant_name == "eternal" for product in SHOP_PRODUCTS)
    assert not any(
        product.species_name in {"floette", "florges"} for product in SHOP_PRODUCTS
    )


def test_groomer_products_include_the_natural_form_and_confirmed_trims() -> None:
    products = {product.id: product for product in SHOP_PRODUCTS}
    assert products["furfrou_natural"].variant_name is None
    assert products["furfrou_natural"].cost.get(CandyType.NORMAL) == 45
    assert [products[f"furfrou_{trim}"].variant_name for trim in FURFROU_TRIMS] == list(
        FURFROU_TRIMS
    )
    assert all(
        products[f"furfrou_{trim}"].cost.get(CandyType.NORMAL) == 65
        for trim in FURFROU_TRIMS
    )


def test_catalog_has_expected_store_sizes() -> None:
    assert sum(product.store is ShopStore.TECHNOLOGY for product in SHOP_PRODUCTS) == 6
    assert sum(product.store is ShopStore.FOSSIL for product in SHOP_PRODUCTS) == 15
    assert sum(product.store is ShopStore.GARDEN for product in SHOP_PRODUCTS) == 22
    assert sum(product.store is ShopStore.GROOMER for product in SHOP_PRODUCTS) == 10
