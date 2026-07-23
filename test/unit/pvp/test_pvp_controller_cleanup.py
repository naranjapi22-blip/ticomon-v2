from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from poke_env.player import Player
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

import application.pvp.pvp_application_service as pvp_service_module  # noqa: F401
import infrastructure.battle.poke_env.pvp_controller as controller_module
from infrastructure.battle.poke_env.pvp_controller import ManualPvpPlayer


def _player_for_message(monkeypatch, error):
    protocol = AsyncMock()
    snapshots = []
    finished = []
    battle = SimpleNamespace(finished=True)

    player = object.__new__(ManualPvpPlayer)
    player.trainer_id = 10
    player.opponent_id = 20
    player._callbacks = SimpleNamespace(
        on_protocol=protocol,
        on_snapshot=snapshots.append,
        on_finished=finished.append,
    )
    player._battles = {"battle-1": battle}
    player._finished_battles = set()
    player._finished_battle_ids = set()
    player._pending_finished_battles = []
    player._capture_sprite_urls = {}
    player._pokeapi_ids = {}
    player._closing = False
    player._log_context = ""
    player._first_message_logged = False
    player._first_request_logged = False
    player._first_snapshot_logged = False
    player._schedule_callback = lambda coroutine: asyncio.create_task(coroutine)
    player._callbacks.on_snapshot = AsyncMock(side_effect=snapshots.append)
    player._callbacks.on_finished = AsyncMock(side_effect=finished.append)

    async def inherited_handler(_self, _messages):
        raise error

    monkeypatch.setattr(Player, "_handle_battle_message", inherited_handler)
    monkeypatch.setattr(
        controller_module,
        "snapshot_battle",
        lambda *_args, **_kwargs: {"final": True},
    )
    return player, protocol, snapshots, finished, battle


@pytest.mark.asyncio
async def test_normal_socket_close_after_win_still_publishes_final_state(monkeypatch):
    player, protocol, snapshots, finished, battle = _player_for_message(
        monkeypatch, ConnectionClosedOK(None, None)
    )

    await player._handle_battle_message([["battle", "win", "Papel"]])
    await asyncio.sleep(0)

    protocol.assert_awaited_once()
    player._callbacks.on_snapshot.assert_awaited_once()
    player._callbacks.on_finished.assert_awaited_once_with(battle)


@pytest.mark.asyncio
async def test_unexpected_socket_close_is_not_suppressed(monkeypatch):
    player, _protocol, _snapshots, _finished, _battle = _player_for_message(
        monkeypatch, ConnectionClosedError(None, None)
    )

    with pytest.raises(ConnectionClosedError):
        await player._handle_battle_message([["battle", "win", "Papel"]])
