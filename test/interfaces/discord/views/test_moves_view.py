from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.creature.creature_loadout_service import CreatureLoadout
from core.creature.move import CreatureMove
from interfaces.discord.views.moves_view import MoveLoadoutView, render_loadout


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
