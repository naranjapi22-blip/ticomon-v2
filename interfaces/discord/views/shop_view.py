import logging

import discord

from core.shop.catalog import (
    ALCREMIE_CREAMS,
    ALCREMIE_DECORATIONS,
    ShopStore,
)
from interfaces.discord.application_emojis import candy_emoji_prefix
from interfaces.discord.images import (
    download_gif_file,
    get_creature_gif,
    get_species_gif,
)

logger = logging.getLogger(__name__)


_VARIANT_LABELS = {
    "highplains": "High Plains",
    "icysnow": "Icy Snow",
    "lareine": "La Reine",
}
_MISSING_PREVIEW_PRODUCTS: set[str] = set()


def _variant_label(name: str) -> str:
    return _VARIANT_LABELS.get(name, name.replace("-", " ").title())


def _product_label(product) -> str:
    if product.display_name is not None:
        return product.display_name
    if product.variant_name is not None:
        return (
            f"{product.species_name.title()} ({_variant_label(product.variant_name)})"
        )
    return product.species_name.title()


def _cost_text(bundle, emoji_index=None) -> str:
    return " + ".join(
        f"{candy_emoji_prefix(emoji_index or {}, candy_type)}"
        f"{amount} {candy_type.value.title()}"
        for candy_type, amount in bundle.items()
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


def _bundle_inventory_text(inventory, bundle, emoji_index=None) -> str:
    return "\n".join(
        f"{candy_emoji_prefix(emoji_index or {}, candy_type)}"
        f"{candy_type.value.title()}: {inventory.get_amount(candy_type)}"
        for candy_type, _ in bundle.items()
    )


def _bundle_cost_text(bundle, emoji_index=None) -> str:
    return "\n".join(
        f"{candy_emoji_prefix(emoji_index or {}, candy_type)}"
        f"{candy_type.value.title()}: {amount}"
        for candy_type, amount in bundle.items()
    )


def _missing_text(inventory, bundle, emoji_index=None) -> str:
    return "\n".join(
        f"Missing: {amount - inventory.get_amount(candy_type)} "
        f"{candy_emoji_prefix(emoji_index or {}, candy_type)}"
        f"{candy_type.value.title()}"
        for candy_type, amount in bundle.items()
        if inventory.get_amount(candy_type) < amount
    )


async def _shop_preview_file(core, preview):
    try:
        creature = await core.shop_application.preview_creature(preview)
        try:
            return await download_gif_file(get_creature_gif(creature), "shop.gif")
        except Exception:
            if preview.product_id not in _MISSING_PREVIEW_PRODUCTS:
                _MISSING_PREVIEW_PRODUCTS.add(preview.product_id)
                logger.warning(
                    "shop_preview_resource_missing product=%s", preview.product_id
                )
            return await download_gif_file(
                get_species_gif(creature.species.pokeapi_id, False), "shop.gif"
            )
    except Exception:
        logger.debug("shop_preview_fallback_missing product=%s", preview.product_id)
        return None


async def _show_purchase_preview(
    core, trainer_id, interaction, preview, message, emoji_index=None
) -> None:
    view = ShopConfirmationViewWithButtons(
        core, trainer_id, preview, emoji_index=emoji_index
    )
    view.message = message
    gif_file = await _shop_preview_file(core, preview)
    await interaction.edit_original_response(
        embed=view.embed(gif_file is not None),
        attachments=[gif_file] if gif_file is not None else [],
        view=view,
    )


class ShopView(discord.ui.View):
    def __init__(self, core, trainer_id: int, emoji_index=None) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.emoji_index = emoji_index or {}
        self.message = None
        self._add_store_buttons()

    def _add_store_buttons(self) -> None:
        self.clear_items()
        for store, label in (
            (ShopStore.TECHNOLOGY, "Technology"),
            (ShopStore.FOSSIL, "Fossil Lab"),
            (ShopStore.PASTRY, "Pastry Shop"),
            (ShopStore.GARDEN, "Garden"),
            (ShopStore.GROOMER, "Pokémon Groomer"),
        ):
            self.add_item(StoreButton(self, store, label))
        self.add_item(CloseShopButton(row=1))

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
        elif store is ShopStore.GARDEN:
            view = GardenView(self.core, self.trainer_id)
            embed = view.menu_embed()
        else:
            view = ProductView(
                self.core,
                self.trainer_id,
                store,
                emoji_index=self.emoji_index,
            )
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
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0)
        self.store = store

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.show_store(interaction, self.store)


class CloseShopButton(discord.ui.Button):
    def __init__(self, row: int | None = None) -> None:
        super().__init__(label="Close", style=discord.ButtonStyle.secondary, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(content="Shop closed.", view=self.view)


class ProductView(discord.ui.View):
    def __init__(
        self,
        core,
        trainer_id: int,
        store: ShopStore,
        products=None,
        title=None,
        emoji_index=None,
    ) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.store = store
        self.emoji_index = emoji_index or {}
        self.message = None
        self._title = title or self._default_title()
        products = products or core.shop_application.products(store)
        options = [
            discord.SelectOption(
                label=_product_label(product),
                value=product.id,
                description=_cost_text(product.cost, self.emoji_index),
            )
            for product in products
        ]
        self.add_item(ProductSelect(options))
        self.add_item(BackToStoresButton())

    def menu_embed(self) -> discord.Embed:
        return discord.Embed(
            title=self._title,
            description="Choose a creature. Prices use type-specific candies.",
            color=discord.Color.blue(),
        )

    def _default_title(self) -> str:
        return {
            ShopStore.TECHNOLOGY: "Technology Shop",
            ShopStore.FOSSIL: "Fossil Lab",
            ShopStore.GARDEN: "Garden",
            ShopStore.GROOMER: "Pokémon Groomer",
        }[self.store]

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
        await _show_purchase_preview(
            self.core,
            self.trainer_id,
            interaction,
            preview,
            self.message,
            self.emoji_index,
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
        view = ShopView(
            self.view.core,
            self.view.trainer_id,
            self.view.emoji_index,
        )
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
                "Random combination: 60 Fairy\n"
                "Choose cream: 90 Fairy\n"
                "Choose cream and decoration: 120 Fairy"
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
        await _show_purchase_preview(
            self.core, self.trainer_id, interaction, preview, self.message
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


class GardenView(discord.ui.View):
    def __init__(self, core, trainer_id: int) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.message = None
        self.add_item(GardenButton("Flabébé colors", "flabebe"))
        self.add_item(GardenButton("Vivillon random", "vivillon_random"))
        self.add_item(GardenButton("Choose Vivillon pattern", "vivillon"))
        self.add_item(BackToStoresButton())

    def menu_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Garden",
            description="Choose a floral variant or a Vivillon pattern.",
            color=discord.Color.green(),
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "This shop belongs to another trainer.", ephemeral=True
            )
            return False
        return True

    async def choose(self, interaction: discord.Interaction, choice: str) -> None:
        products = self.core.shop_application.products(ShopStore.GARDEN)
        if choice == "vivillon_random":
            for item in self.children:
                item.disabled = True
            await interaction.response.defer()
            try:
                preview = await self.core.shop_application.preview_product(
                    self.trainer_id, "vivillon_random"
                )
            except ValueError as error:
                await interaction.edit_original_response(
                    content=str(error), embed=None, attachments=[], view=None
                )
                return
            await _show_purchase_preview(
                self.core, self.trainer_id, interaction, preview, self.message
            )
            return

        species_name = "flabebe" if choice == "flabebe" else "vivillon"
        selected = tuple(
            product
            for product in products
            if product.species_name == species_name and product.id != "vivillon_random"
        )
        title = "Flabébé Colors" if choice == "flabebe" else "Vivillon Patterns"
        view = ProductView(
            self.core,
            self.trainer_id,
            ShopStore.GARDEN,
            products=selected,
            title=title,
        )
        view.message = self.message
        await interaction.response.edit_message(embed=view.menu_embed(), view=view)


class GardenButton(discord.ui.Button):
    def __init__(self, label: str, choice: str) -> None:
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.choice = choice

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.choose(interaction, self.choice)


class ShopConfirmationView(discord.ui.View):
    def __init__(self, core, trainer_id: int, preview, emoji_index=None) -> None:
        super().__init__(timeout=180)
        self.core = core
        self.trainer_id = trainer_id
        self.preview = preview
        self.emoji_index = emoji_index or {}
        self.message = None
        self._processing = False

    def embed(self, has_image: bool = False) -> discord.Embed:
        affordable = self.preview.inventory.has(self.preview.cost)
        self._set_confirm_enabled(affordable)
        product_name = self.preview.species_name.title()
        if self.preview.variant_name is not None:
            product_name += f" ({_variant_label(self.preview.variant_name)})"
        description = f"Product: **{product_name}**\n"
        if affordable:
            current = _bundle_inventory_text(
                self.preview.inventory, self.preview.cost, self.emoji_index
            )
            remaining = _bundle_inventory_text(
                self._remaining(), self.preview.cost, self.emoji_index
            )
            description += (
                f"Current balance:\n{current}\n"
                f"Price:\n{_bundle_cost_text(self.preview.cost, self.emoji_index)}\n"
                f"Balance after purchase:\n{remaining}"
            )
        else:
            current = _bundle_inventory_text(
                self.preview.inventory,
                self.preview.cost,
                self.emoji_index,
            )
            price = _bundle_cost_text(self.preview.cost, self.emoji_index)
            missing = _missing_text(
                self.preview.inventory,
                self.preview.cost,
                self.emoji_index,
            )
            description += (
                "**Insufficient candies**\n"
                f"{current}\n"
                f"Price:\n{price}\n"
                f"{missing}"
            )
        if self.preview.cream:
            description += (
                f"\nCream: **{self.preview.cream}**"
                f"\nDecoration: **{self.preview.decoration}**"
            )
        if not has_image:
            description += (
                "\nPreview image unavailable; the purchase remains available."
            )
        embed = discord.Embed(title="Confirm purchase", description=description)
        if has_image:
            embed.set_image(url="attachment://shop.gif")
        return embed

    def _remaining(self):
        remaining = type(self.preview.inventory)(dict(self.preview.inventory.items()))
        try:
            remaining.consume(self.preview.cost)
        except ValueError:
            pass
        return remaining

    def _set_confirm_enabled(self, enabled: bool) -> None:
        for item in self.children:
            if isinstance(item, ConfirmPurchaseButton):
                item.disabled = not enabled

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
        except Exception as error:
            logger.error(
                "shop_purchase_failed_without_traceback stage=application "
                "trainer_id=%s error_type=%s",
                self.trainer_id,
                type(error).__name__,
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
                f"Purchased **{self._product_name(result)}** "
                f"(#{result.creature.collection_number}).\n"
                f"Remaining candies: {_inventory_text(result.remaining)}"
            ),
            embed=None,
            attachments=[],
            view=None,
        )

    @staticmethod
    def _product_name(result) -> str:
        name = result.creature.species.name.title()
        if result.creature.current_form is not None:
            name += f" ({_variant_label(result.creature.current_form.name)})"
        return name


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
    def __init__(self, core, trainer_id: int, preview, emoji_index=None) -> None:
        super().__init__(core, trainer_id, preview, emoji_index=emoji_index)
        self.add_item(ConfirmPurchaseButton())
        self.add_item(CancelPurchaseButton())
