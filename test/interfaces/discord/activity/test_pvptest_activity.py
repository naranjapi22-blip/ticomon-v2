from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from application.pvp.models import (
    PvpAction,
    PvpActionKind,
    PvpEvent,
    PvpLegalActions,
)
from application.pvp.pvp_application_service import PvpApplicationService
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from core.pvp.session import PvpPhase, PvpSessionRegistry
from interfaces.discord.activity.pvptest_registry import (
    PvptestActivityRegistry,
    event_to_dto,
    legal_actions_to_dto,
    pokemon_to_dto,
)
from interfaces.discord.activity.server import PvptestActivityServer


class FakeService:
    def __init__(self):
        self.registry = PvpSessionRegistry()
        self.legal = {}
        self.submitted = []

    def legal_actions_for(self, session_id, trainer_id):
        return self.legal[(session_id, trainer_id)]

    async def submit_action(self, session_id, trainer_id, action):
        self.submitted.append((session_id, trainer_id, action))
        return True


def _snapshot(player_id=10):
    pokemon = PvpPokemonSnapshot(
        species_name="Pikachu",
        form_name=None,
        current_hp=80,
        max_hp=100,
        hp_fraction=0.8,
        status=None,
        fainted=False,
        sprite_identifier="pikachu",
    )
    return PvpBattleSnapshot(
        turn=2,
        player_id=player_id,
        opponent_id=20,
        player_active=pokemon,
        opponent_active=pokemon,
        player_remaining=2,
        opponent_remaining=1,
        force_switch_player=False,
        force_switch_opponent=False,
        finished=False,
        winner_id=None,
        tie=False,
        player_team=(pokemon,),
        opponent_team=(pokemon,),
    )


@pytest.mark.asyncio
async def test_activity_registry_matches_channel_instance_and_rejects_unrelated_user():
    service = FakeService()
    session = service.registry.create(10, 20)
    registry = PvptestActivityRegistry(service)
    await registry.bind(
        session_id=session.id,
        guild_id=1,
        channel_id=99,
        player_ids=(10, 20),
        display_names={10: "Darwin", 20: "Papel"},
    )
    sent = []

    async def send(payload):
        sent.append(payload)

    assert (
        await registry.connect(
            session_id=session.id,
            user_id=10,
            guild_id=1,
            channel_id=99,
            instance_id="activity-1",
            send_json=send,
        )
        == "player1"
    )
    assert (
        await registry.connect(
            session_id=session.id,
            user_id=30,
            guild_id=1,
            channel_id=99,
            instance_id="activity-1",
            send_json=send,
        )
        == "unauthorized"
    )
    with pytest.raises(PermissionError):
        await registry.connect(
            session_id=session.id,
            user_id=20,
            guild_id=1,
            channel_id=99,
            instance_id="activity-2",
            send_json=send,
        )
    assert sent[0]["role"] == "player1"
    assert sent[-1]["role"] == "unauthorized"


@pytest.mark.asyncio
async def test_registry_rejects_second_active_battle_in_one_channel():
    service = FakeService()
    registry = PvptestActivityRegistry(service)
    first = service.registry.create(10, 20)
    second = service.registry.create(30, 40)
    await registry.bind(
        session_id=first.id,
        guild_id=1,
        channel_id=99,
        player_ids=(10, 20),
        display_names={},
    )
    with pytest.raises(ValueError, match="already active"):
        await registry.bind(
            session_id=second.id,
            guild_id=1,
            channel_id=99,
            player_ids=(30, 40),
            display_names={},
        )


@pytest.mark.asyncio
async def test_registry_cleanup_removes_channel_mapping():
    service = FakeService()
    session = service.registry.create(10, 20)
    registry = PvptestActivityRegistry(service)
    await registry.bind(
        session_id=session.id,
        guild_id=1,
        channel_id=99,
        player_ids=(10, 20),
        display_names={},
    )

    await registry.cleanup(session.id)

    assert registry.find_for_channel(99) is None


def test_activity_dtos_do_not_expose_internal_action_identifiers():
    action = PvpAction(
        kind=PvpActionKind.MOVE,
        identifier="internal-showdown-id",
        label="Thunderbolt",
        detail="PP 15/15",
        move_type="electric",
        category="special",
    )
    dto = legal_actions_to_dto(PvpLegalActions(moves=(action,)))
    assert dto["moves"] == [
        {
            "slot": 1,
            "kind": "move",
            "name": "Thunderbolt",
            "detail": "PP 15/15",
            "type": "electric",
            "category": "special",
            "pp": "PP 15/15",
            "hp_current": None,
            "hp_max": None,
            "fainted": False,
        }
    ]
    assert "identifier" not in dto["moves"][0]


def test_activity_event_and_pokemon_dtos_are_serializable():
    event = event_to_dto(
        PvpEvent(move_name="Thunderbolt", damage=25, actor="player1", target="player2")
    )
    assert event["kind"] == "move"
    pokemon = pokemon_to_dto(_snapshot().player_active, player_side=True)
    assert pokemon["name"] == "Pikachu"
    assert pokemon["sprite_url"].endswith("/PVP/back/pikachu.gif")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "legal",
    [
        PvpLegalActions(
            moves=(PvpAction(PvpActionKind.MOVE, "move:tackle", "Tackle"),)
        ),
        PvpLegalActions(
            switches=(PvpAction(PvpActionKind.SWITCH, "switch:bench", "Bench"),),
            forced_switch=True,
        ),
    ],
)
async def test_activity_action_handler_matches_request_action_contract(legal):
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(10, 20)
    session.phase = (
        PvpPhase.FORCED_SWITCH if legal.forced_switch else PvpPhase.WAITING_FOR_ACTIONS
    )
    activity = PvptestActivityRegistry(service)
    await activity.bind(
        session_id=session.id,
        guild_id=1,
        channel_id=100,
        player_ids=(10, 20),
        display_names={},
    )
    service._action_handlers[session.id] = activity.action_handler(session.id)

    request = asyncio.create_task(service.request_action(session.id, 10, legal))
    await asyncio.sleep(0)

    assert set(activity.get(session.id).deadlines) == {10}
    request.cancel()
    with suppress(asyncio.CancelledError):
        await request


@pytest.mark.asyncio
async def test_activity_action_handlers_keep_sessions_isolated():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    first = service.challenge(10, 20)
    second = service.challenge(30, 40)
    first.phase = PvpPhase.WAITING_FOR_ACTIONS
    second.phase = PvpPhase.FORCED_SWITCH
    activity = PvptestActivityRegistry(service)
    await activity.bind(
        session_id=first.id,
        guild_id=1,
        channel_id=100,
        player_ids=(10, 20),
        display_names={},
    )
    await activity.bind(
        session_id=second.id,
        guild_id=1,
        channel_id=200,
        player_ids=(30, 40),
        display_names={},
    )
    service._action_handlers[first.id] = activity.action_handler(first.id)
    service._action_handlers[second.id] = activity.action_handler(second.id)
    first_legal = PvpLegalActions(
        moves=(PvpAction(PvpActionKind.MOVE, "move:tackle", "Tackle"),)
    )
    second_legal = PvpLegalActions(
        switches=(PvpAction(PvpActionKind.SWITCH, "switch:bench", "Bench"),),
        forced_switch=True,
    )

    requests = [
        asyncio.create_task(service.request_action(first.id, 10, first_legal)),
        asyncio.create_task(service.request_action(second.id, 30, second_legal)),
    ]
    await asyncio.sleep(0)

    assert set(activity.get(first.id).deadlines) == {10}
    assert set(activity.get(second.id).deadlines) == {30}
    for request in requests:
        request.cancel()
    for request in requests:
        with suppress(asyncio.CancelledError):
            await request


@pytest.mark.asyncio
async def test_rejected_activity_origin_logs_only_safe_request_metadata(
    monkeypatch, caplog
):
    monkeypatch.setenv("ACTIVITY_ALLOWED_ORIGINS", "https://allowed.example")
    server = PvptestActivityServer(object())
    request = make_mocked_request(
        "POST",
        "/api/activity/auth",
        headers={
            "Origin": "https://blocked.example",
            "Authorization": "Bearer session-token",
            "Cookie": "session=session-token",
        },
    )
    handler_called = False

    async def handler(_request):
        nonlocal handler_called
        handler_called = True
        return web.json_response({"unexpected": True})

    with caplog.at_level(logging.WARNING, logger="interfaces.discord.activity.server"):
        response = await server._cors_middleware(request, handler)

    assert response.status == 403
    assert not handler_called
    assert response.text == '{"error": "Origin is not allowed."}'
    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert "method=POST" in message
    assert "path=/api/activity/auth" in message
    assert "'https://blocked.example'" in message
    assert "{'https://allowed.example'}" in message
    assert "session-token" not in message
    assert "unexpected" not in message
