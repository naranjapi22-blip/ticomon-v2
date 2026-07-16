from types import SimpleNamespace

import pytest

from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.candy.candy_type import CandyType
from core.creature.creature import Creature
from core.creature.ivs import IVs
from core.creature.nature import Nature
from core.creature.size import Size
from core.shop.catalog import ShopStore
from interfaces.discord.views.shop_view import (
    PastrySelectionView,
    ProductView,
    ShopConfirmationViewWithButtons,
    ShopView,
)
from test.factories import create_species


class Application:
    def products(self, store):
        from core.shop.catalog import SHOP_PRODUCTS

        return tuple(product for product in SHOP_PRODUCTS if product.store is store)


class Core:
    shop_application = Application()


def test_shop_starts_with_three_store_buttons():
    view = ShopView(Core(), 113100351531417600)
    assert [item.label for item in view.children[:3]] == [
        "Technology",
        "Fossil Lab",
        "Pastry Shop",
    ]


def test_product_view_exposes_all_fossils_in_catalog_order():
    view = ProductView(Core(), 7, ShopStore.FOSSIL)
    select = view.children[0]
    assert len(select.options) == 15
    assert select.options[0].value == "omanyte"
    assert select.options[-1].value == "arctovish"


def test_pastry_selection_exposes_nine_canonical_creams():
    view = PastrySelectionView(Core(), 7, "custom")
    select = view.children[0]
    assert len(select.options) == 9
    assert all(
        "cream" in option.value or "swirl" in option.value for option in select.options
    )


class Response:
    def __init__(self, events):
        self.events = events

    async def defer(self):
        self.events.append("defer")


class Interaction:
    def __init__(self, events):
        self.user = SimpleNamespace(id=7)
        self.response = Response(events)
        self.events = events

    async def edit_original_response(self, **kwargs):
        self.events.append(("edit", kwargs))


@pytest.mark.asyncio
async def test_confirmation_defers_and_ignores_double_click():
    species = create_species(name="porygon")
    creature = Creature(
        species=species,
        trainer_id=7,
        ivs=IVs(1, 1, 1, 1, 1, 1),
        size=Size(1.0),
        nature=Nature("hardy"),
        is_shiny=False,
        current_form=None,
    )
    preview = SimpleNamespace(
        species_name="porygon",
        cost=CandyBundle.from_amounts(CandyTypeAmount()),
        inventory=CandyInventory({CandyType.NORMAL: 80}),
        store=ShopStore.TECHNOLOGY,
        cream=None,
        decoration=None,
    )
    preview.cost = CandyBundle.from_amounts(CandyTypeAmount())
    calls = []

    class Application:
        async def purchase(self, trainer_id, selected):
            calls.append(selected)
            return SimpleNamespace(creature=creature, remaining=preview.inventory)

    class PurchaseCore:
        shop_application = Application()

    view = ShopConfirmationViewWithButtons(PurchaseCore(), 7, preview)
    events = []
    interaction = Interaction(events)
    await view.confirm(interaction)
    await view.confirm(interaction)
    assert events[0] == "defer"
    assert len(calls) == 1


def make_preview(inventory, cost, species_name="alcremie"):
    return SimpleNamespace(
        species_name=species_name,
        cost=cost,
        inventory=inventory,
        store=ShopStore.PASTRY,
        cream="vanilla-cream",
        decoration="berry",
    )


def test_alcremie_confirmation_shows_only_fairy_and_subtracts_balance():
    preview = make_preview(
        CandyInventory({CandyType.FAIRY: 107, CandyType.NORMAL: 47}),
        CandyBundle.from_amounts(CandyTypeAmount(CandyType.FAIRY, 80)),
    )
    view = ShopConfirmationViewWithButtons(Core(), 7, preview)
    description = view.embed().description
    assert "Fairy: 107" in description
    assert "Fairy: 80" in description
    assert "Fairy: 27" in description
    assert "Normal" not in description


def test_two_type_confirmation_shows_only_required_types():
    preview = make_preview(
        CandyInventory(
            {CandyType.ELECTRIC: 133, CandyType.FIRE: 113, CandyType.NORMAL: 47}
        ),
        CandyBundle.from_amounts(
            CandyTypeAmount(CandyType.ELECTRIC, 70),
            CandyTypeAmount(CandyType.FIRE, 70),
        ),
        species_name="rotom",
    )
    view = ShopConfirmationViewWithButtons(Core(), 7, preview)
    description = view.embed().description
    assert "Electric: 63" in description
    assert "Fire: 43" in description
    assert "Normal" not in description


def test_insufficient_balance_disables_confirm_and_shows_missing_amount():
    preview = make_preview(
        CandyInventory({CandyType.NORMAL: 47}),
        CandyBundle.from_amounts(CandyTypeAmount(CandyType.NORMAL, 80)),
        species_name="porygon",
    )
    view = ShopConfirmationViewWithButtons(Core(), 7, preview)
    description = view.embed().description
    confirm = next(item for item in view.children if item.label == "Confirm")
    assert confirm.disabled
    assert "Insufficient candies" in description
    assert "Normal: 47" in description
    assert "Missing: 33 Normal" in description
    assert "Balance after purchase" not in description


def test_confirmation_does_not_mutate_preview_inventory():
    inventory = CandyInventory({CandyType.FAIRY: 107})
    preview = make_preview(
        inventory,
        CandyBundle.from_amounts(CandyTypeAmount(CandyType.FAIRY, 80)),
    )
    ShopConfirmationViewWithButtons(Core(), 7, preview).embed()
    assert inventory.get_amount(CandyType.FAIRY) == 107


class CandyTypeAmount:
    def __init__(self, candy_type=CandyType.NORMAL, amount=80):
        self.type = candy_type
        self.amount = amount
