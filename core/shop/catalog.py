from dataclasses import dataclass
from enum import StrEnum

from core.candy.candy_amount import CandyAmount
from core.candy.candy_bundle import CandyBundle
from core.candy.candy_type import CandyType


class ShopStore(StrEnum):
    TECHNOLOGY = "technology"
    FOSSIL = "fossil"
    PASTRY = "pastry"


@dataclass(frozen=True, slots=True)
class ShopProduct:
    id: str
    store: ShopStore
    species_name: str
    cost: CandyBundle
    variant_name: str | None = None


def _cost(*items: tuple[CandyType, int]) -> CandyBundle:
    return CandyBundle.from_amounts(
        *(CandyAmount(candy_type, amount) for candy_type, amount in items)
    )


def _product(
    product_id: str,
    store: ShopStore,
    species_name: str,
    *items: tuple[CandyType, int],
    variant_name: str | None = None,
) -> ShopProduct:
    return ShopProduct(product_id, store, species_name, _cost(*items), variant_name)


SHOP_PRODUCTS: tuple[ShopProduct, ...] = (
    _product("porygon", ShopStore.TECHNOLOGY, "porygon", (CandyType.NORMAL, 80)),
    _product(
        "rotom",
        ShopStore.TECHNOLOGY,
        "rotom",
        (CandyType.ELECTRIC, 50),
        (CandyType.GHOST, 50),
    ),
    _product(
        "rotom_heat",
        ShopStore.TECHNOLOGY,
        "rotom",
        (CandyType.ELECTRIC, 70),
        (CandyType.FIRE, 70),
        variant_name="heat",
    ),
    _product(
        "rotom_wash",
        ShopStore.TECHNOLOGY,
        "rotom",
        (CandyType.ELECTRIC, 70),
        (CandyType.WATER, 70),
        variant_name="wash",
    ),
    _product(
        "rotom_mow",
        ShopStore.TECHNOLOGY,
        "rotom",
        (CandyType.ELECTRIC, 70),
        (CandyType.GRASS, 70),
        variant_name="mow",
    ),
    _product(
        "golett",
        ShopStore.TECHNOLOGY,
        "golett",
        (CandyType.GROUND, 60),
        (CandyType.GHOST, 60),
    ),
    _product(
        "omanyte",
        ShopStore.FOSSIL,
        "omanyte",
        (CandyType.ROCK, 80),
        (CandyType.WATER, 80),
    ),
    _product(
        "kabuto",
        ShopStore.FOSSIL,
        "kabuto",
        (CandyType.ROCK, 80),
        (CandyType.WATER, 80),
    ),
    _product(
        "aerodactyl",
        ShopStore.FOSSIL,
        "aerodactyl",
        (CandyType.ROCK, 80),
        (CandyType.FLYING, 80),
    ),
    _product(
        "lileep",
        ShopStore.FOSSIL,
        "lileep",
        (CandyType.ROCK, 80),
        (CandyType.GRASS, 80),
    ),
    _product(
        "anorith",
        ShopStore.FOSSIL,
        "anorith",
        (CandyType.ROCK, 80),
        (CandyType.BUG, 80),
    ),
    _product("cranidos", ShopStore.FOSSIL, "cranidos", (CandyType.ROCK, 160)),
    _product(
        "shieldon",
        ShopStore.FOSSIL,
        "shieldon",
        (CandyType.ROCK, 80),
        (CandyType.STEEL, 80),
    ),
    _product(
        "tirtouga",
        ShopStore.FOSSIL,
        "tirtouga",
        (CandyType.WATER, 80),
        (CandyType.ROCK, 80),
    ),
    _product(
        "archen",
        ShopStore.FOSSIL,
        "archen",
        (CandyType.ROCK, 80),
        (CandyType.FLYING, 80),
    ),
    _product(
        "tyrunt",
        ShopStore.FOSSIL,
        "tyrunt",
        (CandyType.ROCK, 100),
        (CandyType.DRAGON, 100),
    ),
    _product(
        "amaura",
        ShopStore.FOSSIL,
        "amaura",
        (CandyType.ROCK, 100),
        (CandyType.ICE, 100),
    ),
    _product(
        "dracozolt",
        ShopStore.FOSSIL,
        "dracozolt",
        (CandyType.ELECTRIC, 110),
        (CandyType.DRAGON, 110),
    ),
    _product(
        "arctozolt",
        ShopStore.FOSSIL,
        "arctozolt",
        (CandyType.ELECTRIC, 110),
        (CandyType.ICE, 110),
    ),
    _product(
        "dracovish",
        ShopStore.FOSSIL,
        "dracovish",
        (CandyType.WATER, 110),
        (CandyType.DRAGON, 110),
    ),
    _product(
        "arctovish",
        ShopStore.FOSSIL,
        "arctovish",
        (CandyType.WATER, 110),
        (CandyType.ICE, 110),
    ),
)

ALCREMIE_CREAMS: tuple[str, ...] = (
    "caramel-swirl",
    "lemon-cream",
    "matcha-cream",
    "mint-cream",
    "rainbow-swirl",
    "ruby-cream",
    "ruby-swirl",
    "salted-cream",
    "vanilla-cream",
)
ALCREMIE_DECORATIONS: tuple[str, ...] = (
    "berry",
    "clover",
    "love",
    "ribbon",
    "star",
)


def alcremie_variant_name(cream: str, decoration: str) -> str:
    if cream not in ALCREMIE_CREAMS:
        raise ValueError("Unsupported Alcremie cream.")
    if decoration not in ALCREMIE_DECORATIONS:
        raise ValueError("Unsupported Alcremie decoration.")
    return f"{cream}-{decoration}"


def alcremie_cost(mode: str) -> CandyBundle:
    amounts = {"random": 80, "cream": 120, "custom": 160}
    try:
        amount = amounts[mode]
    except KeyError as error:
        raise ValueError("Unsupported Alcremie purchase mode.") from error
    return _cost((CandyType.FAIRY, amount))
