import logging

import discord

from interfaces.discord.application_emojis import candy_emoji_prefix
from interfaces.discord.images import (
    download_gif_file,
    get_creature_gif,
    get_species_gif,
)

logger = logging.getLogger(__name__)
_MISSING_COLLECTION_RESOURCES: set[tuple[int, int | None]] = set()


def _reward_text(milestone, emoji_index=None) -> str:
    rewards = [
        f"{candy_emoji_prefix(emoji_index or {}, candy_type)}"
        f"{amount} {candy_type.value.title()}"
        for candy_type, amount in milestone.candies.items()
    ]
    if milestone.mints:
        rewards.append(
            f"{milestone.mints} Nature Mint" f"{'s' if milestone.mints != 1 else ''}"
        )
    return " + ".join(rewards)


async def _entry_file(core, entry):
    creature = core.collection_application.preview_creature(entry)
    try:
        return await download_gif_file(get_creature_gif(creature), "collection.gif")
    except Exception:
        key = entry.identity
        if key not in _MISSING_COLLECTION_RESOURCES:
            _MISSING_COLLECTION_RESOURCES.add(key)
            logger.warning(
                "collection_preview_resource_missing species_id=%s variant_id=%s",
                *key,
            )
        try:
            return await download_gif_file(
                get_species_gif(creature.species.pokeapi_id, False), "collection.gif"
            )
        except Exception:
            return None


class _OwnedCollectionView(discord.ui.View):
    def __init__(
        self, core, trainer_id: int, *, timeout: float = 180, emoji_index=None
    ) -> None:
        super().__init__(timeout=timeout)
        self.core = core
        self.trainer_id = trainer_id
        self.emoji_index = emoji_index or {}
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.trainer_id:
            await interaction.response.send_message(
                "These collections belong to another trainer.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                logger.debug("Collection view timeout message was unavailable.")


class CollectionsOverviewView(_OwnedCollectionView):
    def __init__(self, core, trainer_id: int, albums, emoji_index=None) -> None:
        super().__init__(core, trainer_id, emoji_index=emoji_index)
        self.albums = albums
        self.add_item(CollectionAlbumSelect(albums))
        self.add_item(CollectionCloseButton())

    def embed(self) -> discord.Embed:
        lines = [
            f"**{album.definition.name}** — "
            f"{album.progress.historical_count}/{album.progress.total} "
            f"({album.progress.percentage}%)"
            for album in self.albums
        ]
        return discord.Embed(
            title="TicoMon Collections",
            description="\n".join(lines) + "\n\nChoose an album to review it.",
            color=discord.Color.gold(),
        )

    async def choose_album(self, interaction: discord.Interaction, collection_id: str):
        try:
            album = next(
                item for item in self.albums if str(item.definition.id) == collection_id
            )
        except StopIteration:
            await interaction.response.edit_message(
                content="Unknown collection.", embed=None, view=None
            )
            return
        view = CollectionAlbumView(
            self.core,
            self.trainer_id,
            album,
            self.albums,
            self.emoji_index,
        )
        view.message = self.message
        await interaction.response.edit_message(embed=view.embed(), view=view)


class CollectionAlbumSelect(discord.ui.Select):
    def __init__(self, albums) -> None:
        super().__init__(
            placeholder="Choose a collection",
            options=[
                discord.SelectOption(
                    label=album.definition.name,
                    value=str(album.definition.id),
                    description=(
                        f"{album.progress.historical_count}/{album.progress.total} "
                        f"({album.progress.percentage}%)"
                    ),
                )
                for album in albums
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.choose_album(interaction, self.values[0])


class CollectionCloseButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Close", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="Collections closed.",
            view=self.view,
        )


class CollectionAlbumView(_OwnedCollectionView):
    def __init__(
        self, core, trainer_id: int, album, albums=None, emoji_index=None
    ) -> None:
        super().__init__(core, trainer_id, emoji_index=emoji_index)
        self.album = album
        self.albums = albums or (album,)
        self.add_item(CollectionEntriesButton())
        for milestone in album.available_milestones:
            self.add_item(CollectionClaimButton(milestone.threshold))
        self.add_item(CollectionsBackButton())

    def embed(self) -> discord.Embed:
        album = self.album
        milestones = []
        for milestone in album.definition.milestones:
            if milestone.threshold in album.claimed_milestones:
                status = "Claimed"
            elif milestone.threshold > album.progress.historical_count:
                status = "Locked"
            elif milestone.threshold > album.progress.owned_count:
                status = (
                    "Reward not claimable yet; "
                    "historical progress complete; "
                    f"currently owned {album.progress.owned_count}/"
                    f"{milestone.threshold} required"
                )
            else:
                status = "Available"
            milestones.append(
                f"{status}: **{milestone.threshold}/{album.progress.total}** — "
                f"{_reward_text(milestone, self.emoji_index)}"
            )
        return discord.Embed(
            title=album.definition.name,
            description=(
                f"Historical progress: **{album.progress.historical_count}/"
                f"{album.progress.total}** "
                f"({album.progress.percentage}%)\n"
                f"Currently owned: **{album.progress.owned_count}/"
                f"{album.progress.total}**\n\n" + "\n".join(milestones)
            ),
            color=discord.Color.gold(),
        )

    async def show_entries(self, interaction: discord.Interaction) -> None:
        view = CollectionEntriesView(
            self.core,
            self.trainer_id,
            self.album,
            albums=self.albums,
        )
        view.message = self.message
        await interaction.response.edit_message(embed=view.embed(), view=view)

    async def claim(self, interaction: discord.Interaction, threshold: int) -> None:
        for item in self.children:
            item.disabled = True
        await interaction.response.defer()
        try:
            result = await self.core.collection_application.claim(
                self.trainer_id,
                str(self.album.definition.id),
                threshold,
            )
        except ValueError as error:
            await interaction.edit_original_response(
                content=str(error), embed=None, attachments=[], view=None
            )
            return
        albums = tuple(
            result.album if item.definition.id == result.album.definition.id else item
            for item in self.albums
        )
        view = CollectionAlbumView(
            self.core,
            self.trainer_id,
            result.album,
            albums,
            self.emoji_index,
        )
        view.message = self.message
        content = (
            f"Claimed {_reward_text(result.milestone, self.emoji_index)}."
            if result.claimed
            else "That collection reward was already claimed."
        )
        await interaction.edit_original_response(
            content=content, embed=view.embed(), attachments=[], view=view
        )

    async def back(self, interaction: discord.Interaction) -> None:
        view = CollectionsOverviewView(
            self.core,
            self.trainer_id,
            self.albums,
            self.emoji_index,
        )
        view.message = self.message
        await interaction.response.edit_message(embed=view.embed(), view=view)


class CollectionEntriesButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Review Entries", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.show_entries(interaction)


class CollectionClaimButton(discord.ui.Button):
    def __init__(self, threshold: int) -> None:
        super().__init__(
            label=f"Claim Reward ({threshold})",
            style=discord.ButtonStyle.success,
        )
        self.threshold = threshold

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.claim(interaction, self.threshold)


class CollectionsBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.back(interaction)


class CollectionEntriesView(_OwnedCollectionView):
    PAGE_SIZE = 10

    def __init__(
        self, core, trainer_id: int, album, page: int = 0, albums=None
    ) -> None:
        super().__init__(core, trainer_id)
        self.album = album
        self.page = page
        self.albums = albums or (album,)
        self.add_item(CollectionEntrySelect(self.entries_on_page))
        self.add_item(CollectionEntriesPreviousButton())
        self.add_item(CollectionEntriesNextButton())
        self.add_item(CollectionEntriesBackButton())
        self._set_navigation_state()

    @property
    def entries_on_page(self):
        start = self.page * self.PAGE_SIZE
        return self.album.entries[start : start + self.PAGE_SIZE]

    @property
    def page_count(self) -> int:
        return max(1, (len(self.album.entries) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

    def _set_navigation_state(self) -> None:
        for item in self.children:
            if isinstance(item, CollectionEntriesPreviousButton):
                item.disabled = self.page == 0
            elif isinstance(item, CollectionEntriesNextButton):
                item.disabled = self.page >= self.page_count - 1

    def embed(self) -> discord.Embed:
        lines = [
            f"{self._entry_status(entry)} {entry.definition.label} — "
            f"{self._entry_status_text(entry)}"
            for entry in self.entries_on_page
        ]
        return discord.Embed(
            title=f"{self.album.definition.name} Entries",
            description=(
                f"Page {self.page + 1}/{self.page_count}\n\n" + "\n".join(lines)
            ),
            color=discord.Color.gold(),
        )

    @staticmethod
    def _entry_status(entry) -> str:
        if entry.currently_owned:
            return "✅"
        if entry.historically_obtained:
            return "◉"
        return "❌"

    @staticmethod
    def _entry_status_text(entry) -> str:
        if entry.currently_owned:
            return "Obtained and currently owned"
        if entry.historically_obtained:
            return "Obtained historically, not currently owned"
        return "Never obtained"

    async def show_entry(self, interaction: discord.Interaction, index: int) -> None:
        entry = self.entries_on_page[index]
        await interaction.response.defer()
        gif_file = await _entry_file(self.core, entry)
        view = CollectionEntryDetailView(
            self.core,
            self.trainer_id,
            self.album,
            self.page,
            self.albums,
        )
        view.message = self.message
        description = (
            f"Status: **{self._entry_status_text(entry)}**\n"
            f"Source: **{entry.source.title() if entry.source else 'Not obtained'}**"
        )
        if entry.collection_number is not None:
            description += f"\nCollection number: **#{entry.collection_number}**"
        if entry.definition.shop_available and not entry.historically_obtained:
            description += "\nAvailable in `!shop`."
        if gif_file is None:
            description += "\nPreview image unavailable."
        embed = discord.Embed(
            title=entry.definition.label,
            description=description,
            color=discord.Color.gold(),
        )
        if gif_file is not None:
            embed.set_image(url="attachment://collection.gif")
        await interaction.edit_original_response(
            embed=embed,
            attachments=[gif_file] if gif_file is not None else [],
            view=view,
        )

    async def change_page(
        self,
        interaction: discord.Interaction,
        direction: int,
    ) -> None:
        view = CollectionEntriesView(
            self.core,
            self.trainer_id,
            self.album,
            self.page + direction,
            self.albums,
        )
        view.message = self.message
        await interaction.response.edit_message(embed=view.embed(), view=view)

    async def back(self, interaction: discord.Interaction) -> None:
        view = CollectionAlbumView(
            self.core,
            self.trainer_id,
            self.album,
            self.albums,
        )
        view.message = self.message
        await interaction.response.edit_message(embed=view.embed(), view=view)


class CollectionEntrySelect(discord.ui.Select):
    def __init__(self, entries) -> None:
        super().__init__(
            placeholder="Review an entry",
            options=[
                discord.SelectOption(
                    label=entry.definition.label[:100],
                    value=str(index),
                    description=CollectionEntriesView._entry_status_text(entry),
                )
                for index, entry in enumerate(entries)
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.show_entry(interaction, int(self.values[0]))


class CollectionEntriesPreviousButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Previous", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.change_page(interaction, -1)


class CollectionEntriesNextButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Next", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.change_page(interaction, 1)


class CollectionEntriesBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.back(interaction)


class CollectionEntryDetailView(_OwnedCollectionView):
    def __init__(self, core, trainer_id: int, album, page: int, albums=None) -> None:
        super().__init__(core, trainer_id)
        self.album = album
        self.page = page
        self.albums = albums or (album,)
        self.add_item(CollectionEntryDetailBackButton())

    async def back(self, interaction: discord.Interaction) -> None:
        view = CollectionEntriesView(
            self.core,
            self.trainer_id,
            self.album,
            self.page,
            self.albums,
        )
        view.message = self.message
        await interaction.response.edit_message(
            embed=view.embed(), attachments=[], view=view
        )


class CollectionEntryDetailBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label="Back to Entries", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.back(interaction)
