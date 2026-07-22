from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.pvp.models import PvpEvent
from application.pvp.pvp_application_service import PvpApplicationService
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from core.pvp.session import PvpPhase, PvpSessionRegistry
from interfaces.discord.views.pvp_challenge_view import PvpBoardView


def _snapshot(*, finished=False, event=None):
    return PvpBattleSnapshot(
        turn=10,
        player_id=1,
        opponent_id=2,
        player_active=PvpPokemonSnapshot("Zacian", None, 198, 198, 1.0, None, False),
        opponent_active=PvpPokemonSnapshot("Tyranitar", None, 0, 201, 0.0, "FNT", True),
        player_remaining=3,
        opponent_remaining=0,
        force_switch_player=False,
        force_switch_opponent=False,
        finished=finished,
        winner_id=1 if finished else None,
        tie=False,
        last_decisive_event=event,
        last_decisive_event_turn=10 if event else None,
    )


def test_finished_session_can_only_advance_to_cleaned_up():
    session = PvpSessionRegistry().create(1, 2)
    session.phase = PvpPhase.FINALIZING
    session.finish()
    assert session.phase is PvpPhase.FINISHED

    session.mark_cleaned_up()
    session.mark_cleaned_up()
    assert session.phase is PvpPhase.CLEANED_UP

    with pytest.raises(ValueError):
        session.finish()


@pytest.mark.asyncio
async def test_cleanup_is_idempotent_and_rejects_late_delivery():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    await service.cleanup(session.id)

    assert session.phase is PvpPhase.CLEANED_UP
    await service.cleanup(session.id)
    await service.handle_snapshot(session.id, _snapshot())
    await service.finish_from_controller(session.id, None, winner_id=1)
    assert service.is_cleaned_up(session.id)


@pytest.mark.asyncio
async def test_cleaned_up_board_timeout_does_not_edit_discord():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    message = SimpleNamespace(edit=AsyncMock())
    board = PvpBoardView(
        SimpleNamespace(
            core=SimpleNamespace(pvp_application_service=service),
            session_id=session.id,
            message=message,
            display_names={1: "Orange", 2: "Jorroco"},
        )
    )

    await service.cleanup(session.id)
    await board.on_timeout()

    message.edit.assert_not_awaited()


def test_final_snapshot_keeps_structured_decisive_event():
    event = PvpEvent(
        actor="Zacian",
        target="Tyranitar",
        move_name="Play Rough",
        damage=201,
        direct_damage=201,
        damage_source="direct",
        fainted=True,
    )
    snapshot = _snapshot(finished=True, event=event)

    assert snapshot.finished
    assert snapshot.last_decisive_event == event
    assert snapshot.last_decisive_event_turn == 10
    assert snapshot.opponent_active.current_hp == 0
    assert snapshot.opponent_active.status == "FNT"
    assert snapshot.opponent_remaining == 0
