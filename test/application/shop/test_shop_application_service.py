import pytest

from application.shop.shop_application_service import ShopApplicationService
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
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
    assert preview.cost.get(CandyType.ELECTRIC) == 70
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
        CandyRepository(CandyInventory({CandyType.FAIRY: 80})),
        ShopRepository(CandyInventory({CandyType.FAIRY: 80})),
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
    assert result.remaining.get_amount(CandyType.FAIRY) == 27
    assert repository.args[-1] == preview.idempotency_key


class SaltedLoveRandom:
    def choice(self, values):
        return "salted-cream" if len(values) == 9 else "love"


class FixedRandom:
    def choice(self, values):
        return values[-1]
