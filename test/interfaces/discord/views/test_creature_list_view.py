from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from interfaces.discord.views.creature_list_view import CreatureListView


def _interaction(user_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(
            edit_message=AsyncMock(),
            send_message=AsyncMock(),
        ),
    )


def _entries(count: int) -> list[str]:
    return [f"#{index} Pikachu — IVs: {index:02d}%" for index in range(1, count + 1)]


@pytest.mark.asyncio
async def test_creature_list_view_shows_ten_entries_per_page() -> None:
    view = CreatureListView(
        author_id=1,
        title="Top Pokémon",
        entries=_entries(11),
    )

    embed = view.build_embed()

    assert embed.title == "Top Pokémon"
    assert embed.description.splitlines() == _entries(10)
    assert embed.footer.text == "Page 1/2"


@pytest.mark.asyncio
async def test_creature_list_view_buttons_change_page() -> None:
    view = CreatureListView(
        author_id=1,
        title="Top Pokémon",
        entries=_entries(11),
    )
    interaction = _interaction()

    await view.next_button.callback(interaction)

    interaction.response.edit_message.assert_awaited_once()
    assert view.page == 1
    embed = interaction.response.edit_message.await_args.kwargs["embed"]
    assert embed.description.splitlines() == _entries(11)[10:]
    assert embed.footer.text == "Page 2/2"

    interaction.response.edit_message.reset_mock()

    await view.previous_button.callback(interaction)

    assert view.page == 0
    embed = interaction.response.edit_message.await_args.kwargs["embed"]
    assert embed.description.splitlines() == _entries(10)
    assert embed.footer.text == "Page 1/2"


@pytest.mark.asyncio
async def test_creature_list_view_rejects_other_users() -> None:
    view = CreatureListView(
        author_id=1,
        title="Recent Pokémon",
        entries=_entries(2),
    )
    interaction = _interaction(user_id=2)

    allowed = await view.interaction_check(interaction)

    assert not allowed
    interaction.response.send_message.assert_awaited_once_with(
        "❌ This isn't your list.",
        ephemeral=True,
    )


@pytest.mark.asyncio
async def test_creature_list_view_disables_buttons_on_timeout() -> None:
    view = CreatureListView(
        author_id=1,
        title="Recent Pokémon",
        entries=_entries(2),
    )
    view.message = AsyncMock()

    await view.on_timeout()

    assert all(child.disabled for child in view.children)
    view.message.edit.assert_awaited_once_with(view=view)
