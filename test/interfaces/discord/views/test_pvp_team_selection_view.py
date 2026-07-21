import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from core.pvp.session import PvpPhase, PvpSessionRegistry
from interfaces.discord.views.creature_selection_view import CreatureSelectionView
from interfaces.discord.views.pvp_challenge_view import (
    PvpBoardView,
    PvpTeamSelectionView,
)


def _interaction(user_id=1, values=("1", "2", "3")):
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        data={"values": list(values)},
        response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
        followup=SimpleNamespace(send=AsyncMock()),
    )


@pytest.mark.asyncio
async def test_pvp_uses_pick_your_team_flow_and_defers_before_slow_query():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    session.phase = PvpPhase.TEAM_SELECTION
    order = []

    async def get_options(_trainer_id):
        order.append("query")
        await asyncio.sleep(0)
        return [(1, "#1 One"), (2, "#2 Two"), (3, "#3 Three")]

    service = SimpleNamespace(
        get_team_selector=get_options,
        select_team=AsyncMock(return_value=()),
    )
    core = SimpleNamespace(pvp_application_service=service)
    view = PvpTeamSelectionView(core, session)
    interaction = _interaction()
    interaction.response.defer = AsyncMock(
        side_effect=lambda **_: order.append("defer")
    )

    await view.children[0].callback(interaction)

    assert order == ["defer", "query"]
    interaction.followup.send.assert_awaited_once()
    assert isinstance(
        interaction.followup.send.await_args.kwargs["view"], CreatureSelectionView
    )


@pytest.mark.asyncio
async def test_shared_picker_rejects_non_owner_and_duplicate_selection():
    picker = CreatureSelectionView(
        owner_id=1,
        required_count=3,
        options=[(1, "One"), (2, "Two"), (3, "Three")],
        on_selected=AsyncMock(),
        success_message=lambda _: "saved",
    )
    other = _interaction(user_id=2)
    assert not await picker.interaction_check(other)
    other.response.send_message.assert_awaited_once()

    duplicate = _interaction(values=("1", "1", "2"))
    await picker.on_select(duplicate)
    duplicate.response.defer.assert_awaited_once_with(ephemeral=True)
    duplicate.followup.send.assert_awaited_once()
    picker._on_selected.assert_not_awaited()


@pytest.mark.asyncio
async def test_shared_picker_saves_after_defer_and_uses_one_followup():
    saved = AsyncMock(return_value="team")
    picker = CreatureSelectionView(
        owner_id=1,
        required_count=3,
        options=[(1, "One"), (2, "Two"), (3, "Three")],
        on_selected=saved,
        success_message=lambda value: value,
    )
    interaction = _interaction()

    await picker.on_select(interaction)

    interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    saved.assert_awaited_once_with([1, 2, 3])
    interaction.followup.send.assert_awaited_once_with("team", ephemeral=True)
    interaction.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_shared_picker_includes_a_valid_success_view():
    success_view = discord.ui.View()
    picker = CreatureSelectionView(
        owner_id=1,
        required_count=3,
        options=[(1, "One"), (2, "Two"), (3, "Three")],
        on_selected=AsyncMock(return_value="team"),
        success_message=lambda value: value,
        success_view=lambda _: success_view,
    )
    interaction = _interaction()

    await picker.on_select(interaction)

    interaction.followup.send.assert_awaited_once_with(
        "team", ephemeral=True, view=success_view
    )


@pytest.mark.asyncio
async def test_shared_picker_reports_functional_selection_errors():
    picker = CreatureSelectionView(
        owner_id=1,
        required_count=3,
        options=[(1, "One"), (2, "Two"), (3, "Three")],
        on_selected=AsyncMock(side_effect=ValueError("team is no longer valid")),
        success_message=lambda value: value,
    )
    interaction = _interaction()

    await picker.on_select(interaction)

    interaction.followup.send.assert_awaited_once()
    message = interaction.followup.send.await_args.args[0]
    assert message.endswith("Could not save team: team is no longer valid")
    assert interaction.followup.send.await_args.kwargs == {"ephemeral": True}


@pytest.mark.asyncio
async def test_shared_picker_does_not_hide_programming_type_errors():
    picker = CreatureSelectionView(
        owner_id=1,
        required_count=3,
        options=[(1, "One"), (2, "Two"), (3, "Three")],
        on_selected=AsyncMock(side_effect=TypeError("programming error")),
        success_message=lambda value: value,
    )
    interaction = _interaction()

    with pytest.raises(TypeError, match="programming error"):
        await picker.on_select(interaction)

    interaction.followup.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_board_coalesces_rapid_public_edits():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=SimpleNamespace(edit=AsyncMock()),
    )
    board = PvpBoardView(source)
    board._edit_interval = 0

    await board._edit_message()
    board.current_event = "latest"
    await board._edit_message()
    await asyncio.sleep(0.01)

    assert source.message.edit.await_count == 1
    assert source.message.edit.await_args.kwargs["content"].endswith(
        "latest\nReady: none"
    )


def test_pvp_board_uses_sanitized_discord_display_names_and_canonical_orientation():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=None,
        display_names={1: "Orange\n", 2: "Jorroco"},
    )
    board = PvpBoardView(source)
    initiator = PvpPokemonSnapshot("Hydrapple", None, 80, 100, 0.8, None, False)
    opponent = PvpPokemonSnapshot("Tsareena", None, 70, 100, 0.7, None, False)
    board.snapshot = PvpBattleSnapshot(
        1, 2, 1, opponent, initiator, 2, 3, False, False, False, None, False
    )

    state = board._visual_state()

    assert state.top.display_name == "Jorroco"
    assert state.bottom.display_name == "Orange"
    assert state.top.active_name == "Tsareena"
    assert state.bottom.active_name == "Hydrapple"
    assert "11310031531417600" not in state.top.display_name


def test_pvp_board_falls_back_to_trainer_without_full_id():
    registry = PvpSessionRegistry()
    session = registry.create(11310031531417600, 2)
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=None,
        display_names={2: "A" * 100},
    )
    board = PvpBoardView(source)

    assert board._visible_name(session.initiator_id) == "Trainer"
    assert board._visible_name(session.opponent_id) == "A" * 24


@pytest.mark.asyncio
async def test_confirm_team_defers_before_slow_start():
    order = []

    async def confirm(_trainer_id):
        order.append("confirm")
        await asyncio.sleep(0)
        return True

    team_view = SimpleNamespace(confirm=confirm)
    from interfaces.discord.views.pvp_challenge_view import PvpTeamConfirmView

    view = PvpTeamConfirmView(team_view)
    interaction = _interaction()
    interaction.response.defer = AsyncMock(
        side_effect=lambda **_: order.append("defer")
    )

    await view.children[0].callback(interaction)

    assert order == ["defer", "confirm"]
    interaction.response.send_message.assert_not_awaited()
    interaction.followup.send.assert_awaited_once()
