import logging

import discord

from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    ShopStore,
)
from interfaces.discord.images import download_gif_file, get_creature_gif

logger = logging.getLogger(__name__)


def _cost_text(bundle) -> str:
    return " + ".join(
        f"{amount} {candy_type.value.title()}" for candy_type, amount in bundle.items()
    )


def _inventory_text(inventory) -> str:
    return (
        ", ".join(
            f"{candy_type.value.title()}: {amount}"
            for candy_type, amount in inventory.items()
            if amount
        )
        or "No candies"
    )


class ShopView(discord.ui.View):
    def __init__(self, core, trainer_id: int) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.message = None
        self._add_store_buttons()

    def _add_store_buttons(self) -> None:
        self.clear_items()
        for store, label in (
            (ShopStore.TECHNOLOGY, "Technology"),
            (ShopStore.FOSSIL, "Fossil Lab"),
            (ShopStore.PASTRY, "Pastry Shop"),
        ):
            self.add_item(StoreButton(self, store, label))
        self.add_item(CloseShopButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This shop belongs to another trainer.", ephemeral=True
            )
            return False
        return True

    async def show_store(self, interaction: discord.Interaction, store: ShopStore):
        if store is ShopStore.PASTRY:
            view = PastryView(self.core, self.trainer_id)
            embed = view.menu_embed()
        else:
            view = ProductView(self.core, self.trainer_id, store)
            embed = view.menu_embed()
        view.message = self.message
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                logger.debug("Shop view timeout message was unavailable.")


class StoreButton(discord.ui.Button):
    def __init__(self, view: ShopView, store: ShopStore, label: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.store = store

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.show_store(interaction, self.store)


class CloseShopButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Close", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(content="Shop closed.", view=self.view)


class ProductView(discord.ui.View):
    def __init__(self, core, trainer_id: int, store: ShopStore) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.store = store
        self.message = None
        products = core.shop_application.products(store)
        options = [
            discord.SelectOption(
                label=product.species_name.title()
                + (
                    f" ({product.variant_name.title()})" if product.variant_name else ""
                ),
                value=product.id,
                description=_cost_text(product.cost),
            )
            for product in products
        ]
        self.add_item(ProductSelect(options))
        self.add_item(BackToStoresButton())

    def menu_embed(self) -> discord.Embed:
        title = (
            "Technology Shop" if self.store is ShopStore.TECHNOLOGY else "Fossil Lab"
        )
        return discord.Embed(
            title=title,
            description="Choose a creature. Prices use type-specific candies.",
            color=discord.Color.blue(),
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This shop belongs to another trainer.", ephemeral=True
            )
            return False
        return True

    async def select_product(self, interaction: discord.Interaction, product_id: str):
        for item in self.children:
            item.disabled = True
        await interaction.response.defer()
        try:
            preview = await self.core.shop_application.preview_product(
                self.trainer_id, product_id
            )
        except ValueError as error:
            await interaction.edit_original_response(
                content=str(error), embed=None, attachments=[], view=None
            )
            return
        view = ShopConfirmationViewWithButtons(self.core, self.trainer_id, preview)
        view.message = self.message
        await interaction.edit_original_response(
            embed=view.embed(), attachments=[], view=view
        )

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True


class ProductSelect(discord.ui.Select):
    def __init__(self, options) -> None:
        super().__init__(placeholder="Choose a creature", options=options)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.select_product(interaction, self.values[0])


class BackToStoresButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = ShopView(self.view.core, self.view.trainer_id)
        view.message = self.view.message
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="TicoMon Shops",
                description="Choose an establishment.",
                color=discord.Color.green(),
            ),
            view=view,
        )


class PastryView(discord.ui.View):
    def __init__(self, core, trainer_id: int) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.message = None
        self.add_item(PastryModeButton("Random combination", "random"))
        self.add_item(PastryModeButton("Choose cream", "cream"))
        self.add_item(PastryModeButton("Choose both", "custom"))
        self.add_item(BackToStoresButton())

    def menu_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Pastry Shop",
            description=(
                "Random combination: 80 Fairy\n"
                "Choose cream: 120 Fairy\n"
                "Choose cream and decoration: 160 Fairy"
            ),
            color=discord.Color.pink(),
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This shop belongs to another trainer.", ephemeral=True
            )
            return False
        return True

    async def choose_mode(self, interaction: discord.Interaction, mode: str) -> None:
        if mode == "random":
            for item in self.children:
                item.disabled = True
            await interaction.response.defer()
            try:
                preview = await self.core.shop_application.preview_alcremie(
                    self.trainer_id, mode
                )
            except ValueError as error:
                await interaction.edit_original_response(
                    content=str(error), embed=None, attachments=[], view=None
                )
                return
            await self.show_preview(interaction, preview)
            return
        view = PastrySelectionView(self.core, self.trainer_id, mode)
        view.message = self.message
        await interaction.response.edit_message(embed=view.embed(), view=view)

    async def show_preview(self, interaction, preview) -> None:
        view = ShopConfirmationViewWithButtons(self.core, self.trainer_id, preview)
        view.message = self.message
        file = None
        try:
            creature = await self.core.shop_application.preview_creature(preview)
            file = await download_gif_file(get_creature_gif(creature), "alcremie.gif")
        except Exception:
            logger.warning(
                "shop_preview_resource_missing product=%s", preview.product_id
            )
        await interaction.edit_original_response(
            embed=view.embed(file is not None),
            attachments=[file] if file is not None else [],
            view=view,
        )


class PastryModeButton(discord.ui.Button):
    def __init__(self, label: str, mode: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.mode = mode

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.choose_mode(interaction, self.mode)


class PastrySelectionView(discord.ui.View):
    def __init__(self, core, trainer_id: int, mode: str) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.mode = mode
        self.message = None
        self.cream = None
        self.add_item(CreamSelect())
        self.add_item(BackToPastryButton())

    def embed(self) -> discord.Embed:
        return discord.Embed(
            title="Pastry Shop",
            description="Choose a cream.",
            color=discord.Color.pink(),
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This shop belongs to another trainer.", ephemeral=True
            )
            return False
        return True

    async def choose_cream(self, interaction, cream: str) -> None:
        self.cream = cream
        if self.mode == "cream":
            for item in self.children:
                item.disabled = True
            await interaction.response.defer()
            try:
                preview = await self.core.shop_application.preview_alcremie(
                    self.trainer_id, self.mode, cream=cream
                )
            except ValueError as error:
                await interaction.edit_original_response(
                    content=str(error), embed=None, attachments=[], view=None
                )
                return
            parent = PastryView(self.core, self.trainer_id)
            parent.message = self.message
            await parent.show_preview(interaction, preview)
            return
        self.clear_items()
        self.add_item(DecorationSelect())
        self.add_item(BackToPastryButton())
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def choose_decoration(self, interaction, decoration: str) -> None:
        for item in self.children:
            item.disabled = True
        await interaction.response.defer()
        try:
            preview = await self.core.shop_application.preview_alcremie(
                self.trainer_id,
                "custom",
                cream=self.cream,
                decoration=decoration,
            )
        except ValueError as error:
            await interaction.edit_original_response(
                content=str(error), embed=None, attachments=[], view=None
            )
            return
        parent = PastryView(self.core, self.trainer_id)
        parent.message = self.message
        await parent.show_preview(interaction, preview)


class CreamSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Choose a cream",
            options=[
                discord.SelectOption(label=item.title(), value=item)
                for item in ALCREMIE_CREAMS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.choose_cream(interaction, self.values[0])


class DecorationSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Choose a decoration",
            options=[
                discord.SelectOption(label=item.title(), value=item)
                for item in ALCREMIE_DECORATIONS
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.choose_decoration(interaction, self.values[0])


class BackToPastryButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = PastryView(self.view.core, self.view.trainer_id)
        view.message = self.view.message
        await interaction.response.edit_message(embed=view.menu_embed(), view=view)


class ShopConfirmationView(discord.ui.View):
    def __init__(self, core, trainer_id: int, preview) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.preview = preview
        self.message = None
        self._processing = False

    def embed(self, has_image: bool = False) -> discord.Embed:
        description = (
            f"Product: **{self.preview.species_name.title()}**\n"
            f"Cost: **{_cost_text(self.preview.cost)}**\n"
            f"Current balance: **{_inventory_text(self.preview.inventory)}**\n"
            f"Balance after purchase: **{_inventory_text(self._remaining())}**"
        )
        if self.preview.cream:
            description += (
                f"\nCream: **{self.preview.cream}**"
                f"\nDecoration: **{self.preview.decoration}**"
            )
        if not has_image and self.preview.store is ShopStore.PASTRY:
            description += (
                "\nPreview image unavailable; the purchase remains available."
            )
        return discord.Embed(title="Confirm purchase", description=description)

    def _remaining(self):
        remaining = type(self.preview.inventory)(dict(self.preview.inventory.items()))
        try:
            remaining.consume(self.preview.cost)
        except ValueError:
            pass
        return remaining

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This shop belongs to another trainer.", ephemeral=True
            )
            return False
        return True

    async def confirm(self, interaction: discord.Interaction) -> None:
        if self._processing:
            return
        self._processing = True
        for item in self.children:
            item.disabled = True
        await interaction.response.defer()
        try:
            result = await self.core.shop_application.purchase(
                self.trainer_id, self.preview
            )
        except ValueError as error:
            await interaction.edit_original_response(
                content=str(error), embed=None, attachments=[], view=None
            )
            return
        except Exception:
            logger.exception(
                "shop_purchase_presentation_failed trainer_id=%s", self.trainer_id
            )
            await interaction.edit_original_response(
                content="The purchase could not be completed.",
                embed=None,
                attachments=[],
                view=None,
            )
            return
        await interaction.edit_original_response(
            content=(
                f"Purchased **{result.creature.species.name.title()}** "
                f"(#{result.creature.collection_number}).\n"
                f"Remaining candies: {_inventory_text(result.remaining)}"
            ),
            embed=None,
            attachments=[],
            view=None,
        )


class ConfirmPurchaseButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Confirm", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.confirm(interaction)


class CancelPurchaseButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Cancel", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="Purchase cancelled.", view=None
        )


class ShopConfirmationViewWithButtons(ShopConfirmationView):
    def __init__(self, core, trainer_id: int, preview) -> None:
        super().__init__(core, trainer_id, preview)
        self.add_item(ConfirmPurchaseButton())
        self.add_item(CancelPurchaseButton())
