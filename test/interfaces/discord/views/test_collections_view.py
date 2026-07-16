from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.collection.catalog import CollectionId
from interfaces.discord.views.collections_view import (
    CollectionAlbumView,
    CollectionEntriesView,
    CollectionsOverviewView,
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
