from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from core.collection.catalog import CollectionId
from interfaces.discord.views.collections_view import (
    CollectionAlbumView,
    CollectionEntriesView,
    CollectionsOverviewView,
    _reward_text,
)


class Interaction:
    def __init__(self, trainer_id=7):
        self.user = SimpleNamespace(id=trainer_id)
        self.response = SimpleNamespace(
            defer=AsyncMock(),
            edit_message=AsyncMock(),
            send_message=AsyncMock(),
        )
        self.edit_original_response = AsyncMock()


def _entry(index, collected=False):
    return SimpleNamespace(
        definition=SimpleNamespace(label=f"Entry {index}", shop_available=index == 0),
        species=SimpleNamespace(id=index + 1, pokeapi_id=index + 1),
        variant=None,
        historically_obtained=collected,
        currently_owned=collected,
        source="shop" if collected else None,
        collection_number=index + 1 if collected else None,
        identity=(index + 1, None),
    )


def _album(*, entries=(), available=(), claimed=frozenset()):
    definition = SimpleNamespace(
        id=CollectionId.FOSSIL_RESTORATION,
        name="Fossil Restoration",
        entries=entries,
        milestones=(),
    )
    progress = SimpleNamespace(
        historical_count=5,
        owned_count=5,
        total=15,
        percentage=33,
    )
    return SimpleNamespace(
        definition=definition,
        entries=entries,
        progress=progress,
        available_milestones=available,
        claimed_milestones=claimed,
    )


def test_overview_uses_one_select_for_all_six_albums():
    albums = tuple(_album() for _ in range(6))
    view = CollectionsOverviewView(SimpleNamespace(), 7, albums)
    select = view.children[0]
    assert len(select.options) == 6


def test_entries_are_paginated_and_keep_statuses():
    entries = tuple(_entry(index, index % 2 == 0) for index in range(12))
    view = CollectionEntriesView(SimpleNamespace(), 7, _album(entries=entries))
    assert len(view.entries_on_page) == 10
    assert view.page_count == 2
    assert "Obtained and currently owned" in view.embed().description
    assert "Never obtained" in view.embed().description


@pytest.mark.asyncio
async def test_claim_defers_before_calling_application():
    milestone = SimpleNamespace(
        threshold=5,
        candies=SimpleNamespace(items=lambda: ()),
        mints=1,
    )
    album = _album(available=(milestone,))
    updated = _album(available=())
    application = SimpleNamespace(
        claim=AsyncMock(
            return_value=SimpleNamespace(
                album=updated,
                milestone=milestone,
                claimed=True,
            )
        )
    )
    core = SimpleNamespace(collection_application=application)
    view = CollectionAlbumView(core, 7, album)
    interaction = Interaction()

    await view.claim(interaction, 5)

    interaction.response.defer.assert_awaited_once()
    application.claim.assert_awaited_once_with(7, "fossil_restoration", 5)
    interaction.edit_original_response.assert_awaited_once()


@pytest.mark.asyncio
async def test_other_trainer_cannot_control_collection_view():
    view = CollectionsOverviewView(SimpleNamespace(), 7, (_album(),))
    interaction = Interaction(trainer_id=8)

    assert await view.interaction_check(interaction) is False
    interaction.response.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_album_selection_and_back_reuse_the_overview_snapshot():
    fossil = _album()
    technology = _album()
    technology.definition.id = CollectionId.TECHNOLOGY
    technology.definition.name = "Technology Collection"
    snapshot = fossil, technology
    application = SimpleNamespace(album=AsyncMock(), albums=AsyncMock())
    core = SimpleNamespace(collection_application=application)
    overview = CollectionsOverviewView(core, 7, snapshot)
    interaction = Interaction()

    await overview.choose_album(interaction, "technology_collection")

    application.album.assert_not_awaited()
    application.albums.assert_not_awaited()
    album_view = interaction.response.edit_message.await_args.kwargs["view"]
    assert isinstance(album_view, CollectionAlbumView)
    assert album_view.album is technology
    assert album_view.albums is snapshot

    interaction = Interaction()
    await album_view.back(interaction)

    application.albums.assert_not_awaited()
    returned_overview = interaction.response.edit_message.await_args.kwargs["view"]
    assert isinstance(returned_overview, CollectionsOverviewView)
    assert returned_overview.albums is snapshot


@pytest.mark.asyncio
async def test_entry_navigation_reuses_the_album_snapshot():
    entries = tuple(_entry(index) for index in range(12))
    album = _album(entries=entries)
    snapshot = (album,)
    application = SimpleNamespace(album=AsyncMock(), albums=AsyncMock())
    core = SimpleNamespace(collection_application=application)
    album_view = CollectionAlbumView(core, 7, album, snapshot)
    interaction = Interaction()

    await album_view.show_entries(interaction)

    entries_view = interaction.response.edit_message.await_args.kwargs["view"]
    assert isinstance(entries_view, CollectionEntriesView)
    assert entries_view.albums is snapshot

    interaction = Interaction()
    await entries_view.change_page(interaction, 1)
    next_page = interaction.response.edit_message.await_args.kwargs["view"]
    assert next_page.albums is snapshot

    interaction = Interaction()
    await next_page.back(interaction)
    returned_album = interaction.response.edit_message.await_args.kwargs["view"]
    assert returned_album.albums is snapshot
    application.album.assert_not_awaited()
    application.albums.assert_not_awaited()


@pytest.mark.asyncio
async def test_entry_detail_and_back_keep_the_album_snapshot():
    album = _album(entries=(_entry(0),))
    snapshot = (album,)
    application = SimpleNamespace(
        album=AsyncMock(),
        albums=AsyncMock(),
        preview_creature=lambda entry: entry,
    )
    core = SimpleNamespace(collection_application=application)
    entries_view = CollectionEntriesView(core, 7, album, albums=snapshot)
    interaction = Interaction()

    with patch(
        "interfaces.discord.views.collections_view._entry_file",
        new=AsyncMock(return_value=None),
    ):
        await entries_view.show_entry(interaction, 0)

    detail = interaction.edit_original_response.await_args.kwargs["view"]
    assert detail.albums is snapshot

    interaction = Interaction()
    await detail.back(interaction)

    returned_entries = interaction.response.edit_message.await_args.kwargs["view"]
    assert returned_entries.albums is snapshot
    application.album.assert_not_awaited()
    application.albums.assert_not_awaited()


def test_mint_rewards_use_the_complete_singular_and_plural_labels():
    no_candies = SimpleNamespace(items=lambda: ())

    singular = _reward_text(SimpleNamespace(candies=no_candies, mints=1))
    plural = _reward_text(SimpleNamespace(candies=no_candies, mints=2))

    assert singular == "1 Nature Mint"
    assert plural == "2 Nature Mints"
