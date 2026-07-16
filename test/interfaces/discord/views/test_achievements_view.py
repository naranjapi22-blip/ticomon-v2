from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.achievement.definition import ACHIEVEMENT_DEFINITIONS
from interfaces.discord.views.achievements_view import AchievementsView


def _status(index: int, family: str, unlocked: bool = False):
    return SimpleNamespace(
        achievement_id=f"achievement_{index}",
        family=family,
        name=f"Achievement {index}",
        description="A test achievement.",
        progress=1 if unlocked else index,
        threshold=1 if unlocked else 25,
        configured_reward=4,
        unlocked_at=__import__("datetime").datetime(2026, 1, 1) if unlocked else None,
        rewarded_candies=None,
        unlocked=unlocked,
    )


@pytest.mark.asyncio
async def test_overview_and_family_navigation() -> None:
    statuses = tuple(_status(i, "Capture", i == 0) for i in range(3))
    statuses += (_status(3, "Types"),)
    view = AchievementsView(7, statuses)

    overview = view.build_embed()
    assert "1/4" in overview.description
    assert "25.0%" in overview.description

    interaction = SimpleNamespace(response=SimpleNamespace(edit_message=AsyncMock()))
    capture_button = next(
        button for button in view.children if button.label == "Capture"
    )
    await capture_button.callback(interaction)
    assert view.family == "Capture"
    assert (
        "Capture" in interaction.response.edit_message.await_args.kwargs["embed"].title
    )


@pytest.mark.asyncio
async def test_previous_next_and_types_pagination() -> None:
    statuses = tuple(_status(i, "Types") for i in range(18))
    view = AchievementsView(7, statuses)
    interaction = SimpleNamespace(response=SimpleNamespace(edit_message=AsyncMock()))
    types_button = next(button for button in view.children if button.label == "Types")
    await types_button.callback(interaction)
    assert view.total_pages == 3
    await view.next_button.callback(interaction)
    assert view.page == 1
    await view.previous_button.callback(interaction)
    assert view.page == 0


@pytest.mark.asyncio
async def test_other_user_is_rejected_and_timeout_disables_buttons() -> None:
    view = AchievementsView(7, (_status(1, "Capture"),))
    response = SimpleNamespace(send_message=AsyncMock(), edit_message=AsyncMock())
    assert not await view.interaction_check(
        SimpleNamespace(user=SimpleNamespace(id=8), response=response)
    )
    response.send_message.assert_awaited_once()
    view.message = SimpleNamespace(edit=AsyncMock())
    await view.on_timeout()
    assert all(button.disabled for button in view.children)
    view.message.edit.assert_awaited_once_with(view=view)


def test_view_supports_full_catalog_without_writes() -> None:
    families = ("Capture", "Pokédex", "Shiny", "Safari", "Trade", "Special")
    statuses = tuple(_status(index, family) for index, family in enumerate(families))
    statuses += tuple(
        _status(index + len(families), "Types")
        for index in range(len(ACHIEVEMENT_DEFINITIONS) - len(families))
    )
    view = AchievementsView(7, statuses)
    assert len(view.statuses) == len(ACHIEVEMENT_DEFINITIONS)
    assert view.family is None
