from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from application.creature.creature_loadout_service import CreatureLoadout
from core.creature.move import CreatureMove
from interfaces.discord.views.moves_view import (
    EMPTY_MOVE,
    MoveEditorView,
    MoveLoadoutView,
    render_loadout,
)


def loadout():
    move = CreatureMove("splash", "Splash", "normal", "Status", None, None, 40)
    creature = SimpleNamespace(
        collection_number=2,
        species=SimpleNamespace(name="Magikarp"),
        ability_id="swift-swim",
        moves=("splash",),
    )
    ability = SimpleNamespace(display_name="Swift Swim")
    return CreatureLoadout(creature, ability, (move,), (move,))


def test_render_shows_ability_and_dash_for_missing_move_values():
    text = render_loadout(loadout())
    assert "Ability: Swift Swim" in text
    assert "Power —" in text
    assert "Accuracy —" in text
    assert "PP 40" in text


def test_loadout_view_has_no_ability_control():
    view = MoveLoadoutView(SimpleNamespace(), loadout(), owner_id=1)
    labels = [getattr(item, "label", "") for item in view.children]
    assert "Change Moves" in labels
    assert not any("Ability" in label for label in labels)


@pytest.mark.asyncio
async def test_loadout_view_rejects_other_users_and_expires():
    view = MoveLoadoutView(SimpleNamespace(), loadout(), owner_id=1)
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=2),
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    assert await view.interaction_check(interaction) is False
    interaction.response.send_message.assert_awaited_once()

    await view.on_timeout()
    assert all(item.disabled for item in view.children)


def test_cancel_starts_from_the_persisted_loadout():
    view = MoveLoadoutView(SimpleNamespace(), loadout(), owner_id=1)
    assert view.loadout.creature.moves == ("splash",)


def test_editor_uses_valid_sentinel_for_empty_slots():
    view = MoveEditorView(SimpleNamespace(), loadout(), owner_id=1)
    selects = [item for item in view.children if isinstance(item, discord.ui.Select)]

    assert len(selects) == 4
    assert all(option.value for select in selects for option in select.options)
    assert all(
        1 <= len(option.value) <= 100 for select in selects for option in select.options
    )
    assert all(select.options[0].value == EMPTY_MOVE for select in selects)


@pytest.mark.asyncio
async def test_empty_sentinel_is_compacted_and_not_persisted():
    service = SimpleNamespace(update_moves=AsyncMock(return_value=loadout()))
    view = MoveEditorView(service, loadout(), owner_id=1)
    select = next(item for item in view.children if isinstance(item, discord.ui.Select))
    select._values = [EMPTY_MOVE]
    interaction = SimpleNamespace(
        response=SimpleNamespace(edit_message=AsyncMock()),
    )

    await select.callback(interaction)

    assert view.selected == []
    assert all(EMPTY_MOVE not in value for value in view.selected)

    await view.save.callback(interaction)
    service.update_moves.assert_awaited_once_with(1, 2, ())


@pytest.mark.asyncio
async def test_editor_rejects_duplicate_moves():
    service = SimpleNamespace(update_moves=AsyncMock())
    view = MoveEditorView(service, loadout(), owner_id=1)
    select = [item for item in view.children if isinstance(item, discord.ui.Select)][1]
    select._values = ["splash"]
    interaction = SimpleNamespace(
        response=SimpleNamespace(send_message=AsyncMock()),
    )

    await select.callback(interaction)

    interaction.response.send_message.assert_awaited_once()
    service.update_moves.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_normalizes_one_to_four_moves_and_rejects_zero():
    service = SimpleNamespace(update_moves=AsyncMock(return_value=loadout()))
    view = MoveEditorView(service, loadout(), owner_id=1)
    interaction = SimpleNamespace(
        response=SimpleNamespace(edit_message=AsyncMock(), send_message=AsyncMock())
    )

    for count in range(1, 5):
        view.selected = [f"move-{index}" for index in range(count)]
        await view.save.callback(interaction)
        assert service.update_moves.await_args.args[2] == tuple(view.selected)

    service.update_moves.reset_mock(side_effect=True)
    service.update_moves.side_effect = ValueError(
        "A creature must equip between one and four moves."
    )
    view.selected = []
    await view.save.callback(interaction)

    service.update_moves.assert_awaited_once_with(1, 2, ())
    interaction.response.send_message.assert_awaited_once()
