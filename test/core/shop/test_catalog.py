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
    assert prices["cranidos"] == {CandyType.ROCK: 160}
    assert prices["omanyte"] == {CandyType.ROCK: 80, CandyType.WATER: 80}
    assert prices["dracozolt"] == {CandyType.ELECTRIC: 110, CandyType.DRAGON: 110}


def test_alcremie_catalog_has_45_canonical_combinations() -> None:
    combinations = {
        alcremie_variant_name(cream, decoration)
        for cream in ALCREMIE_CREAMS
        for decoration in ALCREMIE_DECORATIONS
    }
    assert len(ALCREMIE_CREAMS) == 9
    assert len(ALCREMIE_DECORATIONS) == 5
    assert len(combinations) == 45
    assert alcremie_cost("random").get(CandyType.FAIRY) == 80
    assert alcremie_cost("cream").get(CandyType.FAIRY) == 120
    assert alcremie_cost("custom").get(CandyType.FAIRY) == 160


def test_catalog_has_expected_store_sizes() -> None:
    assert sum(product.store is ShopStore.TECHNOLOGY for product in SHOP_PRODUCTS) == 6
    assert sum(product.store is ShopStore.FOSSIL for product in SHOP_PRODUCTS) == 15
