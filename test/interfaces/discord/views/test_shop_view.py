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


class CandyTypeAmount:
    type = CandyType.NORMAL
    amount = 80
