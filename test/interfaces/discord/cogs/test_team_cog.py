from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from application.team.team_dto import TeamDTO, TeamSlotDTO
from interfaces.discord.cogs.team_cog import TeamCog
from interfaces.discord.views.team_add_modal import TeamAddModal
from interfaces.discord.views.team_launcher_view import TeamLauncherView
from interfaces.discord.views.team_view import TeamView
from test.builders.creature_builder import CreatureBuilder


def _team_with_one_member() -> TeamDTO:
    creature = CreatureBuilder().with_id(101).with_collection_number(7).build()
    return TeamDTO(
        trainer_id=42,
        slots=(
            TeamSlotDTO(
                slot=1,
                creature=creature,
            ),
        ),
    )


@pytest.mark.asyncio
async def test_team_command_sends_launcher_view() -> None:
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=42),
        send=AsyncMock(return_value=SimpleNamespace()),
    )

    cog = TeamCog(SimpleNamespace())
    await cog.team.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    sent_kwargs = ctx.send.await_args.kwargs
    assert isinstance(sent_kwargs["view"], TeamLauncherView)
    assert sent_kwargs["view"].trainer_id == 42


@pytest.mark.asyncio
async def test_launcher_opens_ephemeral_team_view() -> None:
    team = _team_with_one_member()
    core = SimpleNamespace(
        team_application_service=SimpleNamespace(
            get_team=AsyncMock(return_value=team),
        ),
    )
    launcher = TeamLauncherView(
        core,
        trainer_id=42,
    )
    launcher.message = SimpleNamespace(delete=AsyncMock())
    followup_send = AsyncMock(return_value=SimpleNamespace())
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=42),
        client=Mock(fetch_application_emojis=AsyncMock(return_value=[])),
        response=SimpleNamespace(
            defer=AsyncMock(),
        ),
        followup=SimpleNamespace(send=followup_send),
    )

    await launcher.children[0].callback(interaction)

    interaction.response.defer.assert_awaited_once_with(
        ephemeral=True,
        thinking=True,
    )
    followup_send.assert_awaited_once()
    sent_kwargs = followup_send.await_args.kwargs
    assert sent_kwargs["ephemeral"] is True
    assert sent_kwargs["wait"] is True
    assert isinstance(sent_kwargs["view"], TeamView)
    assert sent_kwargs["embed"].title == "Your Team"
    launcher.message.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_button_opens_modal() -> None:
    core = SimpleNamespace(team_application_service=SimpleNamespace())
    view = TeamView(
        core,
        trainer_id=42,
        team=_team_with_one_member(),
    )
    send_modal = AsyncMock()
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=42),
        response=SimpleNamespace(send_modal=send_modal),
    )

    await view.children[0].callback(interaction)

    send_modal.assert_awaited_once()
    modal = send_modal.await_args.args[0]
    assert isinstance(modal, TeamAddModal)


@pytest.mark.asyncio
async def test_remove_last_updates_team_and_replies_ephemerally() -> None:
    team = _team_with_one_member()
    refreshed_team = TeamDTO(trainer_id=42, slots=())
    get_team = AsyncMock(side_effect=[team, refreshed_team])
    remove_from_team = AsyncMock()
    core = SimpleNamespace(
        team_application_service=SimpleNamespace(
            get_team=get_team,
            remove_from_team=remove_from_team,
        ),
    )
    view = TeamView(
        core,
        trainer_id=42,
        team=team,
    )
    view.message = SimpleNamespace(edit=AsyncMock())
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=42),
        response=SimpleNamespace(defer=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )

    await view.children[1].callback(interaction)

    remove_from_team.assert_awaited_once_with(
        trainer_id=42,
        collection_number=7,
    )
    view.message.edit.assert_awaited_once()
    interaction.followup.send.assert_awaited_once()
    assert interaction.followup.send.await_args.kwargs["ephemeral"] is True
