from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import application.pvp.pvp_application_service as pvp_service_module
from application.pvp.events import PvpEventTranslator, display_species_name
from application.pvp.models import PvpAction, PvpActionKind, PvpLegalActions
from application.pvp.pvp_application_service import PvpApplicationService
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
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
async def test_finish_from_controller_notifies_and_cleans_up_once():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    session.battle_controller = SimpleNamespace(close=AsyncMock())
    calls = []
    service._finish_handlers[session.id] = lambda _battle: _record(calls)

    await service.finish_from_controller(session.id, object())
    await service.finish_from_controller(session.id, object())

    assert calls == ["finished"]
    session.battle_controller.close.assert_awaited_once()


async def _record(calls):
    calls.append("finished")


@pytest.mark.asyncio
async def test_terminal_protocol_resolves_generated_username_and_finishes_once():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    calls = []
    session.battle_controller = SimpleNamespace(
        resolve_winner=lambda username: (
            1 if username.casefold() == "tmabc123a1p1" else None
        ),
        close=AsyncMock(),
    )
    service._finish_handlers[session.id] = lambda _battle: _record(calls)

    await service.handle_protocol(session.id, [["battle", "win", "tmABC123a1p1"]])
    await service.handle_protocol(session.id, [["battle", "win", "tmABC123a1p1"]])

    assert calls == ["finished"]
    session.battle_controller.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_terminal_protocol_with_unknown_username_still_finishes():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    calls = []
    session.battle_controller = SimpleNamespace(
        resolve_winner=lambda _username: None,
        close=AsyncMock(),
    )
    service._finish_handlers[session.id] = lambda _battle: _record(calls)

    await service.handle_protocol(
        session.id, [["battle", "win", "unknown-showdown-user"]]
    )

    assert calls == ["finished"]
    session.battle_controller.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_forfeit_uses_the_same_finalization_path():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    controller = SimpleNamespace(forfeit=AsyncMock(), close=AsyncMock())
    session.battle_controller = controller
    calls = []
    service._finish_handlers[session.id] = lambda _battle: _record(calls)

    await service.forfeit(session.id, 1)

    assert calls == ["finished"]
    controller.forfeit.assert_awaited_once_with(1)
    controller.close.assert_awaited_once()


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
    translator = PvpEventTranslator()
    translator.observe_snapshot(
        PvpBattleSnapshot(
            turn=1,
            player_id=1,
            opponent_id=2,
            player_active=PvpPokemonSnapshot(
                "Pikachu", None, 100, 100, 1.0, None, False
            ),
            opponent_active=PvpPokemonSnapshot(
                "Gyarados", None, 100, 100, 1.0, None, False
            ),
            player_remaining=3,
            opponent_remaining=3,
            force_switch_player=False,
            force_switch_opponent=False,
            finished=False,
            winner_id=None,
            tie=False,
        )
    )
    steps = translator.translate(
        [
            ["battle-gen9customgame-1", "move", "p1a: Pikachu", "Thunderbolt"],
            ["battle-gen9customgame-1", "-damage", "p2a: Gyarados", "64/100"],
            ["battle-gen9customgame-1", "unknown-event", "ignored"],
            ["battle-gen9customgame-1", "faint", "p2a: Gyarados"],
        ]
    )

    assert [step.message for step in steps] == [
        "Pikachu used Thunderbolt. Gyarados took 36 damage. "
        "Gyarados was knocked out."
    ]
    assert steps[0].event is not None
    assert steps[0].event.actor == "Pikachu"
    assert steps[0].event.target == "Gyarados"
    assert steps[0].event.damage == 36
    assert "p1a:" not in steps[0].message
    assert "p2a:" not in steps[0].message


def test_event_translator_compacts_initial_entries_and_weather():
    translator = PvpEventTranslator()

    steps = translator.translate(
        [
            ["battle", "switch", "p1a: tyranitar", "Tyranitar, L50"],
            ["battle", "switch", "p2a: ironthorns", "Iron Thorns, L50"],
            ["battle", "-weather", "Sandstorm"],
        ]
    )

    assert [step.message for step in steps] == [
        "Tyranitar and Iron Thorns entered the battle. Sandstorm started."
    ]
    assert "L50" not in steps[0].message
    assert "sent out Tyranitar" not in steps[0].message

    assert translator.translate([["battle", "-weather", "Sandstorm"]]) == ()


def test_event_translator_uses_damage_without_repeating_hp_and_normalizes_names():
    translator = PvpEventTranslator()
    translator.observe_snapshot(
        PvpBattleSnapshot(
            1,
            1,
            2,
            PvpPokemonSnapshot("tyranitar", None, 201, 201, 1.0, None, False),
            PvpPokemonSnapshot("kommoo", None, 167, 167, 1.0, None, False),
            3,
            1,
            False,
            False,
            False,
            None,
            False,
        )
    )

    steps = translator.translate([["battle", "-damage", "p2a: kommoo", "157/167"]])

    assert steps[0].message == "Kommo-o took 10 damage."
    assert "/167" not in steps[0].message
    assert display_species_name("ironthorns") == "Iron Thorns"
    assert display_species_name("kommoo") == "Kommo-o"


@pytest.mark.parametrize(
    ("previous", "current", "expected"), [(212, 0, 212), (50, 0, 50)]
)
def test_ko_damage_uses_positive_hp_delta(previous, current, expected):
    translator = PvpEventTranslator()
    translator.observe_snapshot(
        PvpBattleSnapshot(
            1,
            1,
            2,
            PvpPokemonSnapshot("Garchomp", None, 100, 100, 1.0, None, False),
            PvpPokemonSnapshot("Hydrapple", None, previous, 212, 1.0, None, False),
            3,
            1,
            False,
            False,
            False,
            None,
            False,
        )
    )

    steps = translator.translate(
        [
            ["battle", "move", "p1a: Garchomp", "Outrage"],
            ["battle", "-damage", "p2a: Hydrapple", f"{current}/212"],
            ["battle", "faint", "p2a: Hydrapple"],
        ]
    )

    assert f"{expected} damage" in steps[0].message
    assert "took 0 damage" not in steps[0].message


def test_ko_without_previous_snapshot_omits_damage():
    steps = PvpEventTranslator().translate(
        [
            ["battle", "move", "p1a: Garchomp", "Outrage"],
            ["battle", "-damage", "p2a: Hydrapple", "0/212"],
            ["battle", "faint", "p2a: Hydrapple"],
        ]
    )

    assert steps[0].message == "Garchomp used Outrage. Hydrapple was knocked out."
    assert "took 0 damage" not in steps[0].message


def test_explicit_zero_damage_is_allowed_without_ko():
    translator = PvpEventTranslator()
    translator.observe_snapshot(
        PvpBattleSnapshot(
            1,
            1,
            2,
            PvpPokemonSnapshot("Garchomp", None, 100, 100, 1.0, None, False),
            PvpPokemonSnapshot("Hydrapple", None, 212, 212, 1.0, None, False),
            3,
            1,
            False,
            False,
            False,
            None,
            False,
        )
    )

    steps = translator.translate([["battle", "-damage", "p2a: Hydrapple", "212/212"]])

    assert steps[0].message == "Hydrapple took 0 damage."


def test_canonical_translator_does_not_mix_opposite_client_sides():
    translator = PvpEventTranslator(player_id=1, opponent_id=2)
    translator.observe_snapshot(
        PvpBattleSnapshot(
            9,
            2,
            1,
            PvpPokemonSnapshot("Walking Wake", None, 87, 204, 0.4, None, False),
            PvpPokemonSnapshot("Zacian", None, 198, 198, 1.0, None, False),
            1,
            1,
            False,
            False,
            False,
            None,
            False,
        )
    )

    steps = translator.translate([["battle", "-damage", "p1a: Zacian", "123/198"]])

    assert steps[0].message == "Zacian took 75 damage."
