from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.release.exceptions import ReleaseCreatureAssignedToTeam
from interfaces.discord.views.release_confirm_view import ReleaseConfirmView
from test.builders.creature_builder import CreatureBuilder


@pytest.mark.asyncio
async def test_release_confirm_reports_team_assignment_and_disables_view():
    creature = CreatureBuilder().with_collection_number(123).build()
    core = SimpleNamespace(
        release_application=SimpleNamespace(
            release=AsyncMock(
                side_effect=ReleaseCreatureAssignedToTeam([123]),
            ),
        ),
        creature_repository=SimpleNamespace(
            get_by_collection_numbers=AsyncMock(return_value=[creature]),
        ),
    )
    view = ReleaseConfirmView(core, creature.trainer_id, [123])
    button = view.children[0]
    interaction = SimpleNamespace(
        response=SimpleNamespace(defer=AsyncMock()),
        edit_original_response=AsyncMock(),
    )

    await button.callback(interaction)

    interaction.edit_original_response.assert_awaited_once()
    kwargs = interaction.edit_original_response.await_args.kwargs
    assert "#123" in kwargs["content"]
    assert "assigned to your team" in kwargs["content"]
    assert kwargs["view"] is None
    assert view.is_finished()
