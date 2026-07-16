from core.candy.candy_type import CandyType
from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    SHOP_PRODUCTS,
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
    prices = {product.id: dict(product.cost.items()) for product in SHOP_PRODUCTS}
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


def test_catalog_has_expected_store_sizes() -> None:
    assert sum(product.store is ShopStore.TECHNOLOGY for product in SHOP_PRODUCTS) == 6
    assert sum(product.store is ShopStore.FOSSIL for product in SHOP_PRODUCTS) == 15
