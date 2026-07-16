import pytest

from application.shop.shop_application_service import ShopApplicationService
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    FLABEBE_COLORS,
    FURFROU_TRIMS,
    VIVILLON_PATTERNS,
)
from core.species.variant import Variant
from test.factories import create_species


class SpeciesRepository:
    def __init__(self, species):
        self.species = species

    async def find_by_name(self, name):
        return next((item for item in self.species if item.name.lower() == name), None)


class CandyRepository:
    def __init__(self, inventory):
        self.inventory = inventory

    async def get(self, trainer_id):
        return self.inventory


class ShopRepository:
    def __init__(self, inventory):
        self.inventory = inventory

    async def purchase(self, trainer_id, creature, cost, product_id, key):
        self.args = trainer_id, creature, cost, product_id, key
        remaining = CandyInventory(dict(self.inventory.items()))
        remaining.consume(cost)
        return creature, remaining, True


@pytest.mark.asyncio
async def test_preview_uses_canonical_rotom_variant_and_freezes_key():
    rotom = create_species(
        id=479,
        name="rotom",
        types=["electric", "ghost"],
        variants=[Variant(144, "heat"), Variant(149, "wash"), Variant(146, "mow")],
    )
    inventory = CandyInventory({CandyType.ELECTRIC: 100, CandyType.FIRE: 100})
    candies = CandyRepository(inventory)
    repository = ShopRepository(inventory)
    service = ShopApplicationService(SpeciesRepository([rotom]), candies, repository)
    preview = await service.preview_product(113100351531417600, "rotom_heat")
    assert preview.variant_name == "heat"
    assert preview.cost.get(CandyType.ELECTRIC) == 55
    assert preview.idempotency_key.startswith("shop:113100351531417600:")

    result = await service.purchase(113100351531417600, preview)
    assert result.creature.current_form.name == "heat"
    assert result.creature.is_shiny is False
    assert result.creature.minted_nature is None
    assert repository.args[-1] == preview.idempotency_key


@pytest.mark.asyncio
async def test_random_alcremie_is_one_of_45_supported_combinations():
    variants = [
        Variant(index, f"{cream}-{decoration}")
        for index, (cream, decoration) in enumerate(
            (
                (cream, decoration)
                for cream in (
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
                for decoration in ("berry", "clover", "love", "ribbon", "star")
            ),
            1,
        )
    ]
    alcremie = create_species(id=869, name="alcremie", variants=variants)
    service = ShopApplicationService(
        SpeciesRepository([alcremie]),
        CandyRepository(CandyInventory({CandyType.FAIRY: 60})),
        ShopRepository(CandyInventory({CandyType.FAIRY: 60})),
    )
    preview = await service.preview_alcremie(7, "random", random_source=FixedRandom())
    assert preview.variant_name == "vanilla-cream-star"
    assert preview.cream == "vanilla-cream"
    assert preview.decoration == "star"


@pytest.mark.asyncio
async def test_salted_cream_love_preview_and_purchase_are_identical():
    alcremie = create_species(
        id=869,
        name="alcremie",
        variants=[Variant(80, "salted-cream-love")],
    )
    inventory = CandyInventory({CandyType.FAIRY: 107})
    repository = ShopRepository(inventory)
    service = ShopApplicationService(
        SpeciesRepository([alcremie]), CandyRepository(inventory), repository
    )
    preview = await service.preview_alcremie(
        113100351531417600,
        "random",
        random_source=SaltedLoveRandom(),
    )
    result = await service.purchase(113100351531417600, preview)
    assert preview.variant_id == 80
    assert preview.variant_name == "salted-cream-love"
    assert result.creature.current_form.id == preview.variant_id
    assert result.creature.current_form.name == preview.variant_name
    assert result.creature.is_shiny is False
    assert result.creature.minted_nature is None
    assert result.remaining.get_amount(CandyType.FAIRY) == 47
    assert repository.args[-1] == preview.idempotency_key


@pytest.mark.asyncio
async def test_all_canonical_alcremie_combinations_resolve_without_aliases():
    variants = [
        Variant(index, f"{cream}-{decoration}")
        for index, (cream, decoration) in enumerate(
            (
                (cream, decoration)
                for cream in ALCREMIE_CREAMS
                for decoration in ALCREMIE_DECORATIONS
            ),
            1,
        )
    ]
    variants.append(Variant(99, "saltedcream-love"))
    alcremie = create_species(id=869, name="alcremie", variants=variants)
    service = ShopApplicationService(
        SpeciesRepository([alcremie]),
        CandyRepository(CandyInventory({CandyType.FAIRY: 120})),
        ShopRepository(CandyInventory({CandyType.FAIRY: 120})),
    )

    previews = [
        await service.preview_alcremie(7, "custom", cream=cream, decoration=decoration)
        for cream in ALCREMIE_CREAMS
        for decoration in ALCREMIE_DECORATIONS
    ]

    assert len(previews) == 45
    assert {preview.variant_name for preview in previews} == {
        f"{cream}-{decoration}"
        for cream in ALCREMIE_CREAMS
        for decoration in ALCREMIE_DECORATIONS
    }
    assert "saltedcream-love" not in {preview.variant_name for preview in previews}


@pytest.mark.asyncio
async def test_random_vivillon_freezes_a_confirmed_pattern_for_purchase():
    variants = [Variant(index, name) for index, name in enumerate(VIVILLON_PATTERNS, 1)]
    vivillon = create_species(
        id=666,
        name="vivillon",
        types=["bug", "flying"],
        variants=variants,
    )
    inventory = CandyInventory({CandyType.BUG: 35, CandyType.FLYING: 35})
    repository = ShopRepository(inventory)
    service = ShopApplicationService(
        SpeciesRepository([vivillon]), CandyRepository(inventory), repository
    )

    preview = await service.preview_product(
        113100351531417600,
        "vivillon_random",
        random_source=FixedRandom(),
    )
    result = await service.purchase(113100351531417600, preview)

    assert preview.variant_name == "tundra"
    assert result.creature.current_form.id == preview.variant_id
    assert result.creature.current_form.name == "tundra"
    assert result.remaining.get_amount(CandyType.BUG) == 0
    assert result.remaining.get_amount(CandyType.FLYING) == 0


@pytest.mark.asyncio
async def test_garden_and_groomer_previews_resolve_the_selected_variant():
    flabebe = create_species(
        id=669,
        name="flabebe",
        types=["fairy"],
        variants=[
            Variant(index, color) for index, color in enumerate(FLABEBE_COLORS, 105)
        ],
    )
    furfrou = create_species(
        id=676,
        name="furfrou",
        types=["normal"],
        variants=[
            Variant(index, trim) for index, trim in enumerate(FURFROU_TRIMS, 118)
        ],
    )
    inventory = CandyInventory({CandyType.FAIRY: 45, CandyType.NORMAL: 110})
    service = ShopApplicationService(
        SpeciesRepository([flabebe, furfrou]),
        CandyRepository(inventory),
        ShopRepository(inventory),
    )

    flabebe_previews = [
        await service.preview_product(7, f"flabebe_{color}") for color in FLABEBE_COLORS
    ]
    natural_preview = await service.preview_product(7, "furfrou_natural")
    trim_previews = [
        await service.preview_product(7, f"furfrou_{trim}") for trim in FURFROU_TRIMS
    ]

    assert [preview.variant_name for preview in flabebe_previews] == list(
        FLABEBE_COLORS
    )
    assert natural_preview.variant_id is None
    assert [preview.variant_name for preview in trim_previews] == list(FURFROU_TRIMS)


class SaltedLoveRandom:
    def choice(self, values):
        return "salted-cream" if len(values) == 9 else "love"


class FixedRandom:
    def choice(self, values):
        return values[-1]
