from __future__ import annotations

import asyncio

import pytest

import application.pvp.pvp_application_service as pvp_service_module
from application.pvp.events import PvpEventTranslator
from application.pvp.models import PvpAction, PvpActionKind, PvpLegalActions
from application.pvp.pvp_application_service import PvpApplicationService
from core.pvp.session import PvpPhase, PvpSessionRegistry


def test_session_requires_three_creatures_and_two_confirmations():
    registry = PvpSessionRegistry()
    session = registry.create(1, 2)

    session.select_team(1, (11, 12, 13))
    session.select_team(2, (21, 22, 23))
    assert session.phase is PvpPhase.WAITING_FOR_ACTIONS
    assert not session.confirm_team(1)
    assert session.confirm_team(2)

    session.begin_battle()
    assert session.phase is PvpPhase.WAITING_FOR_ACTIONS
    assert session.turn_number == 1


def test_session_rejects_duplicate_team_members():
    session = PvpSessionRegistry().create(1, 2)

    with pytest.raises(ValueError, match="three different"):
        session.select_team(1, (11, 11, 12))


@pytest.mark.asyncio
async def test_actions_are_private_and_must_be_legal():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    session.phase = PvpPhase.WAITING_FOR_ACTIONS
    legal = PvpLegalActions(
        moves=(PvpAction(PvpActionKind.MOVE, "move:tackle", "Tackle"),),
    )

    waiting = asyncio.create_task(service.request_action(session.id, 1, legal))
    await asyncio.sleep(0)

    with pytest.raises(ValueError, match="not legal"):
        await service.submit_action(
            session.id,
            1,
            PvpAction(PvpActionKind.MOVE, "move:illegal", "Illegal"),
        )

    action = PvpAction(PvpActionKind.MOVE, "move:tackle", "Tackle")
    await service.submit_action(session.id, 1, action)
    assert await waiting == action

    await service.cleanup(session.id)


@pytest.mark.asyncio
async def test_move_timeout_applies_one_legal_action(monkeypatch):
    monkeypatch.setattr(pvp_service_module, "ACTION_TIMEOUT_SECONDS", 0.01)
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    session.phase = PvpPhase.WAITING_FOR_ACTIONS
    legal = PvpLegalActions(
        moves=(PvpAction(PvpActionKind.MOVE, "move:tackle", "Tackle"),)
    )

    action = await service.request_action(session.id, 1, legal)

    assert action in legal.moves
    assert session.selected_actions == {1: action.identifier}


@pytest.mark.asyncio
async def test_forced_switch_timeout_applies_only_a_legal_switch(monkeypatch):
    monkeypatch.setattr(pvp_service_module, "FORCED_SWITCH_TIMEOUT_SECONDS", 0.01)
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    session.phase = PvpPhase.FORCED_SWITCH
    legal = PvpLegalActions(
        switches=(PvpAction(PvpActionKind.SWITCH, "switch:bench", "Bench"),),
        forced_switch=True,
    )

    action = await service.request_action(session.id, 1, legal)

    assert action in legal.switches
    assert session.selected_actions == {1: action.identifier}


@pytest.mark.asyncio
async def test_manual_action_wins_just_before_timeout(monkeypatch):
    monkeypatch.setattr(pvp_service_module, "ACTION_TIMEOUT_SECONDS", 0.05)
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    session.phase = PvpPhase.WAITING_FOR_ACTIONS
    action = PvpAction(PvpActionKind.MOVE, "move:tackle", "Tackle")
    legal = PvpLegalActions(moves=(action,))
    waiting = asyncio.create_task(service.request_action(session.id, 1, legal))
    await asyncio.sleep(0.01)

    assert await service.submit_action(session.id, 1, action)
    assert await waiting == action
    assert session.selected_actions == {1: action.identifier}


@pytest.mark.asyncio
async def test_obsolete_request_does_not_replace_new_request(monkeypatch):
    monkeypatch.setattr(pvp_service_module, "ACTION_TIMEOUT_SECONDS", 0.01)
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    session.phase = PvpPhase.WAITING_FOR_ACTIONS
    first_legal = PvpLegalActions(
        moves=(PvpAction(PvpActionKind.MOVE, "move:first", "First"),)
    )
    second_action = PvpAction(PvpActionKind.MOVE, "move:second", "Second")
    second_legal = PvpLegalActions(moves=(second_action,))

    first = asyncio.create_task(service.request_action(session.id, 1, first_legal))
    await asyncio.sleep(0)
    second = asyncio.create_task(service.request_action(session.id, 1, second_legal))
    await asyncio.sleep(0)
    assert await service.submit_action(session.id, 1, second_action)
    assert await second == second_action
    with pytest.raises(asyncio.CancelledError):
        await first


def test_timeout_action_policy_uses_only_legal_moves():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    legal = PvpLegalActions(
        moves=(PvpAction(PvpActionKind.MOVE, "move:1", "One"),),
        switches=(PvpAction(PvpActionKind.SWITCH, "switch:bench", "Bench"),),
    )

    assert service._automatic_action(legal).kind is PvpActionKind.MOVE


def test_forced_switch_policy_uses_only_legal_switches():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    legal = PvpLegalActions(
        moves=(PvpAction(PvpActionKind.MOVE, "move:1", "One"),),
        switches=(PvpAction(PvpActionKind.SWITCH, "switch:bench", "Bench"),),
        forced_switch=True,
    )

    assert service._automatic_action(legal).kind is PvpActionKind.SWITCH


def test_event_translator_ignores_unknown_protocol_events():
    steps = PvpEventTranslator().translate(
        [
            ["battle-gen9customgame-1", "move", "p1a: Pikachu", "Thunderbolt"],
            ["battle-gen9customgame-1", "-damage", "p2a: Gyarados", "64/100"],
            ["battle-gen9customgame-1", "unknown-event", "ignored"],
            ["battle-gen9customgame-1", "faint", "p2a: Gyarados"],
        ]
    )

    assert [step.message for step in steps] == [
        "Pikachu used Thunderbolt.",
        "Gyarados lost 64/100 HP.",
        "Gyarados fainted.",
    ]
