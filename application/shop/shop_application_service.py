from dataclasses import dataclass, replace
from uuid import uuid4

from core.candy.candy_bundle import CandyBundle
from core.candy.candy_inventory import CandyInventory
from core.creature.creature import Creature
from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity_factory import OpportunityFactory
from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    SHOP_PRODUCTS,
    ShopProduct,
    ShopStore,
    alcremie_cost,
    alcremie_variant_name,
)


@dataclass(frozen=True, slots=True)
class ShopPreview:
    product_id: str
    store: ShopStore
    species_name: str
    cost: CandyBundle
    inventory: CandyInventory
    variant_id: int | None = None
    variant_name: str | None = None
    cream: str | None = None
    decoration: str | None = None
    idempotency_key: str = ""


@dataclass(frozen=True, slots=True)
class ShopPurchaseResult:
    creature: Creature
    remaining: CandyInventory
    created: bool
    preview: ShopPreview


class ShopApplicationService:
    def __init__(self, species_repository, candy_repository, shop_repository) -> None:
        self._species_repository = species_repository
        self._candy_repository = candy_repository
        self._shop_repository = shop_repository

    def products(self, store: ShopStore) -> tuple[ShopProduct, ...]:
        return tuple(product for product in SHOP_PRODUCTS if product.store is store)

    async def preview_product(
        self,
        trainer_id: int,
        product_id: str,
        *,
        variant_id: int | None = None,
    ) -> ShopPreview:
        product = self._product(product_id)
        species = await self._species_repository.find_by_name(product.species_name)
        if species is None:
            raise ValueError(f"Shop species {product.species_name} is unavailable.")

        variant = None
        if product.variant_name is not None:
            variant = self._variant_by_name(species, product.variant_name)
        elif variant_id is not None:
            variant = next(
                (item for item in species.variants or () if item.id == variant_id),
                None,
            )
            if variant is None:
                raise ValueError("The selected variant is unavailable.")

        inventory = await self._candy_repository.get(trainer_id)
        return ShopPreview(
            product.id,
            product.store,
            species.name,
            product.cost,
            inventory,
            variant.id if variant else None,
            variant.name if variant else None,
            idempotency_key=f"shop:{trainer_id}:{uuid4()}",
        )

    async def preview_alcremie(
        self,
        trainer_id: int,
        mode: str,
        *,
        cream: str | None = None,
        decoration: str | None = None,
        random_source=None,
    ) -> ShopPreview:
        if mode == "random":
            cream, decoration = self._choose_alcremie_parts(random_source)
        elif mode == "cream":
            if cream not in ALCREMIE_CREAMS:
                raise ValueError("Unsupported Alcremie cream.")
            decoration = self._choose_decoration(random_source)
        elif mode == "custom":
            if cream not in ALCREMIE_CREAMS:
                raise ValueError("Unsupported Alcremie cream.")
            if decoration not in ALCREMIE_DECORATIONS:
                raise ValueError("Unsupported Alcremie decoration.")
        else:
            raise ValueError("Unsupported Alcremie purchase mode.")

        variant_name = alcremie_variant_name(cream, decoration)
        species = await self._species_repository.find_by_name("alcremie")
        if species is None:
            raise ValueError("Alcremie is unavailable.")
        variant = self._variant_by_name(species, variant_name)
        inventory = await self._candy_repository.get(trainer_id)
        return ShopPreview(
            f"alcremie:{variant.id}",
            ShopStore.PASTRY,
            species.name,
            alcremie_cost(mode),
            inventory,
            variant.id,
            variant.name,
            cream,
            decoration,
            f"shop:{trainer_id}:{uuid4()}",
        )

    async def purchase(
        self,
        trainer_id: int,
        preview: ShopPreview,
    ) -> ShopPurchaseResult:
        if not preview.inventory.has(preview.cost):
            raise ValueError("Insufficient candies for this purchase.")
        species = await self._species_repository.find_by_name(preview.species_name)
        if species is None:
            raise ValueError("Shop species is unavailable.")
        variant = None
        if preview.variant_id is not None:
            variant = next(
                (
                    item
                    for item in species.variants or ()
                    if item.id == preview.variant_id
                ),
                None,
            )
            if variant is None or variant.name != preview.variant_name:
                raise ValueError("The selected variant is unavailable.")

        creature = self._build_creature(trainer_id, species, variant)
        stored, remaining, created = await self._shop_repository.purchase(
            trainer_id,
            creature,
            preview.cost,
            preview.product_id,
            preview.idempotency_key,
        )
        return ShopPurchaseResult(stored, remaining, created, preview)

    async def preview_creature(self, preview):
        species = await self._species_repository.find_by_name(preview.species_name)
        if species is None:
            raise ValueError("Shop species is unavailable.")
        variant = None
        if preview.variant_id is not None:
            variant = next(
                (
                    item
                    for item in species.variants or ()
                    if item.id == preview.variant_id
                ),
                None,
            )
            if variant is None or variant.name != preview.variant_name:
                raise ValueError("The selected variant is unavailable.")
        return self._build_creature(0, species, variant)

    @staticmethod
    def _build_creature(trainer_id, species, variant):
        opportunity = OpportunityFactory.create(species)
        opportunity = replace(opportunity, is_shiny=False, initial_form=variant)
        return CreatureFactory.create(trainer_id, opportunity)

    @staticmethod
    def _product(product_id: str) -> ShopProduct:
        for product in SHOP_PRODUCTS:
            if product.id == product_id:
                return product
        raise ValueError("Shop product not found.")

    @staticmethod
    def _variant_by_name(species, variant_name: str):
        variant = next(
            (item for item in species.variants or () if item.name == variant_name),
            None,
        )
        if variant is None:
            raise ValueError(f"Variant {variant_name} is unavailable.")
        return variant

    @staticmethod
    def _choose_decoration(random_source):
        import random

        return (random_source or random).choice(ALCREMIE_DECORATIONS)

    @classmethod
    def _choose_alcremie_parts(cls, random_source):
        import random

        source = random_source or random
        return source.choice(ALCREMIE_CREAMS), source.choice(ALCREMIE_DECORATIONS)
