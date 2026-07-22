import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
import pytest

from application.pvp.models import (
    PvpAction,
    PvpActionKind,
    PvpEvent,
    PvpLegalActions,
    PvpPresentationStep,
)
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from core.pvp.session import PvpPhase, PvpSessionRegistry
from interfaces.discord.views.creature_selection_view import CreatureSelectionView
from interfaces.discord.views.pvp_challenge_view import (
    PvpActionView,
    PvpBoardView,
    PvpChallengeView,
    PvpTeamSelectionView,
    _action_description,
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
    content = source.message.edit.await_args.kwargs["content"]
    assert content.endswith("latest")
    assert "Waiting for both players" in content


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

    content = board.render()
    assert content.count("Jorroco") == 1
    assert content.count("Orange") == 1
    assert content.count("Turn 1") == 1
    assert "Recent turns" not in content
    assert "Last turn:" not in content
    assert "Tyranitar" not in content


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


def test_pvp_board_uses_real_waiting_phase_and_public_battle_data():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    session.phase = PvpPhase.WAITING_FOR_ACTIONS
    session.turn_number = 6
    session.register_action_request(2, "request-2")
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=None,
        display_names={1: "Orange", 2: "Jorroco"},
    )
    board = PvpBoardView(source)
    board.snapshot = PvpBattleSnapshot(
        6,
        1,
        2,
        PvpPokemonSnapshot("Gardevoir", None, 156, 156, 1.0, None, False),
        PvpPokemonSnapshot("Hydrapple", None, 42, 181, 42 / 181, "PAR", False),
        3,
        2,
        False,
        False,
        False,
        None,
        False,
    )

    content = board.render()

    assert "Orange vs Jorroco" in content
    assert "Turn 6" in content
    assert "Waiting for Jorroco" in content
    assert "Gardevoir" in content and "156/156 HP" in content
    assert "Hydrapple" in content and "42/181 HP · PAR" in content
    assert "3 Pokémon left" in content and "2 Pokémon left" in content
    assert "p1a:" not in content and "p2a:" not in content


def test_pvp_board_uses_both_clients_complete_team_counts():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=None,
        display_names={1: "Orange", 2: "Jorroco"},
    )
    board = PvpBoardView(source)
    initiator = PvpBattleSnapshot(
        5,
        1,
        2,
        PvpPokemonSnapshot("Zacian", None, 88, 198, 88 / 198, None, False),
        PvpPokemonSnapshot("Seismitoad", None, 210, 210, 1.0, None, False),
        3,
        1,
        False,
        False,
        False,
        None,
        False,
    )
    opponent = PvpBattleSnapshot(
        5,
        2,
        1,
        PvpPokemonSnapshot("Seismitoad", None, 210, 210, 1.0, None, False),
        PvpPokemonSnapshot("Zacian", None, 88, 198, 88 / 198, None, False),
        3,
        1,
        False,
        False,
        False,
        None,
        False,
    )
    board._snapshots = {1: initiator, 2: opponent}
    board.snapshot = opponent

    canonical = board._display_snapshot()

    assert canonical.player_remaining == 3
    assert canonical.opponent_remaining == 3
    assert "3 Pokémon left" in board.render()


def test_pvp_board_shows_resolving_and_forced_replacement_phases():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=None,
        display_names={1: "Orange", 2: "Jorroco"},
    )
    board = PvpBoardView(source)

    session.phase = PvpPhase.RESOLVING
    assert "Resolving turn" in board.render()

    session.phase = PvpPhase.FORCED_SWITCH
    session.register_action_request(1, "replacement-1")
    assert "Choose a replacement" in board.render()
    assert "Orange" in board.render()

    session.phase = PvpPhase.FINALIZING
    assert "Battle finished" in board.render()

    board.snapshot = PvpBattleSnapshot(
        5,
        1,
        2,
        PvpPokemonSnapshot("Hydrapple", None, 0, 212, 0.0, "FNT", True),
        PvpPokemonSnapshot("Garchomp", None, 208, 208, 1.0, None, False),
        0,
        1,
        True,
        False,
        False,
        None,
        False,
    )
    assert "Battle finished" in board.render()


def test_private_action_details_include_move_and_switch_information():
    move = PvpAction(
        PvpActionKind.MOVE,
        "move:moonblast",
        "Moonblast",
        detail="PP 15/15",
        move_type="Fairy",
        category="Special",
        power=95,
        accuracy=100,
    )
    switch = PvpAction(
        PvpActionKind.SWITCH,
        "switch:bellibolt",
        "Bellibolt",
        hp_current=140,
        hp_max=214,
        status="PAR",
    )
    actions = PvpLegalActions(moves=(move,), switches=(switch,))

    assert actions.moves[0].detail == "PP 15/15"
    assert actions.switches[0].hp_current == 140
    assert actions.switches[0].status == "PAR"


def test_private_panel_keeps_details_only_in_select_options():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=None,
        display_names={1: "Orange", 2: "Rival"},
    )
    board = PvpBoardView(source)
    move = PvpAction(
        PvpActionKind.MOVE,
        "move:moonblast",
        "moonblast",
        detail="PP 24/24",
        move_type="Fairy",
        category="Special",
        power=95,
        accuracy=100,
    )
    actions = PvpLegalActions(moves=(move,))
    embed = board._build_action_embed(1, actions)
    view = PvpActionView(board, 1, actions)

    assert not embed.fields
    assert view.select.options[0].label == "Moonblast"
    assert _action_description(move) == "Fairy · Special · 95 BP · PP 24/24 · 100% Acc"
    assert "moonblast" not in _action_description(move)


def test_pending_challenge_owns_accept_and_decline_only():
    session = PvpSessionRegistry().create(1, 2)
    view = PvpChallengeView(SimpleNamespace(), session)

    assert [child.label for child in view.children] == ["Accept", "Decline"]


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


@pytest.mark.asyncio
async def test_finished_board_replaces_previous_components_and_announces_winner():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    message = SimpleNamespace(edit=AsyncMock())
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=message,
        display_names={1: "Orange", 2: "Jorroco"},
    )
    board = PvpBoardView(source)
    board._edit_interval = 0
    board.snapshot = PvpBattleSnapshot(
        1,
        1,
        2,
        PvpPokemonSnapshot("Gardevoir", None, 100, 100, 1.0, None, False),
        PvpPokemonSnapshot("Bellibolt", None, 0, 214, 0.0, None, True),
        3,
        0,
        False,
        False,
        True,
        1,
        False,
    )
    board._snapshots[1] = board.snapshot

    await board.finish()

    kwargs = message.edit.await_args.kwargs
    assert kwargs["view"] is None
    assert "Orange won the battle." in kwargs["content"]
    assert board._terminal


@pytest.mark.asyncio
async def test_finished_board_keeps_the_decisive_event_with_the_result():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    session.final_winner_id = 1
    message = SimpleNamespace(edit=AsyncMock())
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=message,
        display_names={1: "Orange", 2: "Jorroco"},
    )
    board = PvpBoardView(source)
    board._edit_interval = 0
    await board.set_event(
        PvpPresentationStep(
            "Zacian used Play Rough. Tyranitar was knocked out.",
            event=PvpEvent(
                actor="Zacian",
                target="Tyranitar",
                move_name="Play Rough",
                damage=150,
                direct_damage=150,
                fainted=True,
            ),
        )
    )

    await board.finish()

    content = message.edit.await_args.kwargs["content"]
    assert content.endswith(
        "Orange won the battle.\n" "Zacian used Play Rough. Tyranitar was knocked out."
    )
    assert content.count("Tyranitar was knocked out.") == 1


@pytest.mark.asyncio
async def test_finished_board_without_final_snapshot_still_delivers_result():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    session.final_winner_id = 2
    message = SimpleNamespace(edit=AsyncMock())
    source = SimpleNamespace(
        core=SimpleNamespace(
            pvp_application_service=SimpleNamespace(registry=registry)
        ),
        session_id=session.id,
        message=message,
        display_names={1: "Orange", 2: "Jorroco"},
    )
    board = PvpBoardView(source)
    board._edit_interval = 0

    await board.finish()

    assert "Jorroco won the battle." in message.edit.await_args.kwargs["content"]
    assert message.edit.await_args.kwargs["view"] is None


@pytest.mark.asyncio
async def test_superseded_challenge_timeout_cannot_restore_components():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    session.phase = PvpPhase.TEAM_SELECTION
    message = SimpleNamespace(edit=AsyncMock())
    service = SimpleNamespace(registry=registry, cleanup=AsyncMock())
    view = PvpChallengeView(
        SimpleNamespace(pvp_application_service=service),
        session,
        {1: "Orange", 2: "Jorroco"},
    )
    view.message = message
    view.superseded = True

    await view.on_timeout()

    message.edit.assert_not_awaited()
    service.cleanup.assert_not_awaited()


@pytest.mark.asyncio
async def test_superseded_team_selection_timeout_cannot_cleanup_active_board():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)
    message = SimpleNamespace(edit=AsyncMock())
    service = SimpleNamespace(registry=registry, cleanup=AsyncMock())
    view = PvpTeamSelectionView(
        SimpleNamespace(pvp_application_service=service),
        session,
        {1: "Orange", 2: "Jorroco"},
    )
    view.message = message
    view.superseded = True

    await view.on_timeout()

    message.edit.assert_not_awaited()
    service.cleanup.assert_not_awaited()
