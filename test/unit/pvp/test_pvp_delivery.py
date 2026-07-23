from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import application.pvp.pvp_application_service as pvp_service_module
from application.pvp.events import (
    PvpEventTranslator,
    display_species_name,
    display_stat_name,
)
from application.pvp.models import PvpAction, PvpActionKind, PvpLegalActions
from application.pvp.pvp_application_service import PvpApplicationService
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot
from application.pvp.task_management import register_task
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
async def test_auto_selection_log_contains_request_and_reason(monkeypatch, caplog):
    monkeypatch.setattr(pvp_service_module, "ACTION_TIMEOUT_SECONDS", 0.01)
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    session.phase = PvpPhase.WAITING_FOR_ACTIONS
    legal = PvpLegalActions(
        moves=(PvpAction(PvpActionKind.MOVE, "move:tackle", "Tackle"),)
    )
    caplog.set_level(logging.WARNING)

    await service.request_action(session.id, 1, legal)

    record = next(
        record
        for record in caplog.records
        if record.message.startswith("pvp_action_auto_selected")
    )
    assert f"session_id={session.id}" in record.getMessage()
    assert "request_id=" in record.getMessage()
    assert "action_type=normal_action" in record.getMessage()
    assert "reason=normal_action_timeout" in record.getMessage()
    assert "legal_moves_count=1" in record.getMessage()


@pytest.mark.asyncio
async def test_startup_watchdog_reports_visible_timeout_and_cleans_session(monkeypatch):
    monkeypatch.setattr(pvp_service_module, "FIRST_SNAPSHOT_TIMEOUT_SECONDS", 0.01)
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    messages = []

    async def collect(message):
        messages.append(message)

    service._event_handlers[session.id] = collect
    service._first_snapshot_events[session.id] = asyncio.Event()

    await service._watch_first_snapshot(session.id)

    assert messages == ["PvP startup timed out before the first battle snapshot."]
    assert service.is_cleaned_up(session.id)


@pytest.mark.asyncio
async def test_background_task_failure_is_logged_without_secret(caplog):
    async def fail():
        raise RuntimeError("Showdown token=secret-value failed")

    task = register_task(
        asyncio.create_task(fail(), name="pvp-test-background-failure"),
        owner="test",
        role="startup",
        log_context="session_id=s guild_id=g channel_id=c player1_id=1 player2_id=2",
    )
    with pytest.raises(RuntimeError):
        await task
    await asyncio.sleep(0)

    assert "pvp_task_failed" in caplog.text
    assert "secret-value" not in caplog.text
    assert "session_id=s" in caplog.text


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


def test_event_translator_preserves_authoritative_move_category():
    translator = PvpEventTranslator()
    translator.set_move_categories(
        PvpLegalActions(
            moves=(
                PvpAction(
                    PvpActionKind.MOVE,
                    "move:surf",
                    "Surf",
                    category="Special",
                ),
                PvpAction(
                    PvpActionKind.MOVE,
                    "move:tackle",
                    "Tackle",
                    category="Physical",
                ),
            )
        )
    )
    steps = translator.translate(
        [
            ["battle", "move", "p1a: Pikachu", "Surf"],
            ["battle", "-damage", "p2a: Gyarados", "50/100"],
        ]
    )
    assert steps[0].event.category == "Special"


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


@pytest.mark.parametrize(
    ("stat", "expected"),
    [("spa", "Sp. Atk"), ("spd", "Sp. Def"), ("atk", "Attack"), ("spe", "Speed")],
)
def test_showdown_stat_names_are_user_facing(stat, expected):
    assert display_stat_name(stat) == expected


@pytest.mark.parametrize(
    ("event", "amount", "expected"),
    [
        ("-unboost", "1", "Hydreigon's Sp. Atk fell."),
        ("-unboost", "2", "Hydreigon's Sp. Atk fell sharply."),
        ("-boost", "1", "Hydreigon's Sp. Atk rose."),
        ("-boost", "2", "Hydreigon's Sp. Atk rose sharply."),
    ],
)
def test_stat_change_magnitude_is_preserved(event, amount, expected):
    translator = PvpEventTranslator()

    steps = translator.translate([["battle", event, "p1a: Hydreigon", "spa", amount]])

    assert steps[0].message == expected
    assert "spa" not in steps[0].message


def test_move_direct_damage_is_separate_from_secondary_damage_and_stat_changes():
    translator = PvpEventTranslator()
    translator.observe_snapshot(
        PvpBattleSnapshot(
            6,
            1,
            2,
            PvpPokemonSnapshot("Hydreigon", None, 24, 199, 24 / 199, None, False),
            PvpPokemonSnapshot("Iron Moth", None, 106, 185, 106 / 185, None, False),
            2,
            2,
            False,
            False,
            False,
            None,
            False,
        )
    )

    steps = translator.translate(
        [
            ["battle", "move", "p1a: Hydreigon", "Draco Meteor", "p2a: Iron Moth"],
            ["battle", "-damage", "p2a: Iron Moth", "95/185"],
            ["battle", "-unboost", "p1a: Hydreigon", "spa", "2"],
            ["battle", "-damage", "p1a: Hydreigon", "12/199", "[from] Sandstorm"],
        ]
    )

    message = steps[0].message
    assert "Hydreigon used Draco Meteor." in message
    assert "Iron Moth took 11 damage." in message
    assert "Hydreigon's Sp. Atk fell sharply." in message
    assert "Sandstorm dealt 12 damage to Hydreigon." in message
    assert "Hydreigon took 12 damage" not in message
    assert "spa" not in message
    assert steps[0].event is not None
    assert steps[0].event.direct_damage == 11
    assert steps[0].event.damage_source == "direct"


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("[from] Recoil", "Hydreigon took 12 recoil damage."),
        ("[from] psn", "Hydreigon took 12 poison damage."),
        ("[from] brn", "Hydreigon took 12 burn damage."),
        ("[from] Life Orb", "Hydreigon took 12 item damage."),
        ("[from] unknown effect", "Hydreigon took 12 indirect damage."),
    ],
)
def test_secondary_damage_keeps_its_cause(tag, expected):
    translator = PvpEventTranslator()
    translator.observe_snapshot(
        PvpBattleSnapshot(
            1,
            1,
            2,
            PvpPokemonSnapshot("Hydreigon", None, 24, 199, 24 / 199, None, False),
            PvpPokemonSnapshot("Iron Moth", None, 100, 185, 100 / 185, None, False),
            2,
            2,
            False,
            False,
            False,
            None,
            False,
        )
    )

    steps = translator.translate(
        [["battle", "-damage", "p1a: Hydreigon", "12/199", tag]]
    )

    assert steps[0].message == expected
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


def _damage_snapshot(turn=2):
    return PvpBattleSnapshot(
        turn,
        1,
        2,
        PvpPokemonSnapshot("Hydrapple", None, 212, 212, 1.0, None, False),
        PvpPokemonSnapshot("Tyranitar", None, 201, 201, 1.0, None, False),
        3,
        3,
        False,
        False,
        False,
        None,
        False,
    )


@pytest.mark.asyncio
async def test_duplicate_damage_is_deduplicated_before_hp_calculation():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    events = []

    async def collect(step):
        events.append(step)

    service._event_handlers[session.id] = collect
    service._event_translators[session.id] = PvpEventTranslator(1, 2)
    await service.handle_snapshot(session.id, _damage_snapshot())
    messages = [
        ["battle", "move", "p1a: Hydrapple", "Leaf Storm", "p2a: Tyranitar"],
        ["battle", "-damage", "p2a: Tyranitar", "49/201"],
    ]

    await service.handle_protocol(session.id, messages, source_player_id=1)
    await service.handle_protocol(session.id, messages, source_player_id=2)

    assert len(events) == 1
    assert "Tyranitar took 152 damage." in events[0].message
    assert events[0].event is not None
    assert events[0].event.direct_damage == 152
    await service.cleanup(session.id)


@pytest.mark.asyncio
async def test_non_canonical_damage_arriving_first_does_not_consume_canonical_event():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    events = []

    async def collect(step):
        events.append(step)

    service._event_handlers[session.id] = collect
    service._event_translators[session.id] = PvpEventTranslator(1, 2)
    await service.handle_snapshot(session.id, _damage_snapshot())
    messages = [
        ["battle", "move", "p1a: Hydrapple", "Leaf Storm", "p2a: Tyranitar"],
        ["battle", "-damage", "p2a: Tyranitar", "49/201"],
    ]

    await service.handle_protocol(session.id, messages, source_player_id=2)
    await service.handle_protocol(session.id, messages, source_player_id=1)

    assert len(events) == 1
    assert "152 damage" in events[0].message
    await service.cleanup(session.id)


@pytest.mark.asyncio
async def test_terminal_batch_delivers_canonical_decisive_event_before_finalization():
    service = PvpApplicationService(registry=PvpSessionRegistry())
    session = service.challenge(1, 2)
    events = []
    snapshots = []

    async def collect(step):
        events.append(step)

    async def collect_snapshot(snapshot):
        snapshots.append(snapshot)

    service._event_handlers[session.id] = collect
    service._event_translators[session.id] = PvpEventTranslator(1, 2)
    service._snapshot_handlers[session.id] = collect_snapshot
    session.turn_number = 2
    await service.handle_snapshot(
        session.id, replace(_damage_snapshot(), opponent_remaining=1)
    )
    session.battle_controller = SimpleNamespace(
        resolve_winner=lambda _username: 1,
        close=AsyncMock(),
    )

    await service.handle_protocol(
        session.id,
        [
            ["battle", "move", "p1a: Hydrapple", "Leaf Storm", "p2a: Tyranitar"],
            ["battle", "-damage", "p2a: Tyranitar", "0/201"],
            ["battle", "faint", "p2a: Tyranitar"],
            ["battle", "win", "Orange"],
        ],
        source_player_id=1,
    )

    assert len(events) == 1
    assert events[0].turn == 2
    assert events[0].event.fainted
    assert events[0].event.direct_damage == 201
    final_snapshot = snapshots[-1]
    assert final_snapshot.last_decisive_event == events[0].event
    assert final_snapshot.opponent_active.current_hp == 0
    assert final_snapshot.opponent_active.status == "FNT"
    assert final_snapshot.opponent_remaining == 0
    assert final_snapshot.player_remaining == 3
    assert session.phase is PvpPhase.CLEANED_UP


def test_event_translator_preserves_each_resolved_action_in_turn_order():
    translator = PvpEventTranslator()
    translator.observe_snapshot(_damage_snapshot(turn=4))

    steps = translator.translate(
        [
            ["battle", "move", "p1a: Hydrapple", "Leaf Storm", "p2a: Tyranitar"],
            ["battle", "-damage", "p2a: Tyranitar", "49/201"],
            ["battle", "move", "p2a: Tyranitar", "Stone Edge", "p1a: Hydrapple"],
            ["battle", "-damage", "p1a: Hydrapple", "124/212"],
        ]
    )

    assert [step.message for step in steps] == [
        "Hydrapple used Leaf Storm. Tyranitar took 152 damage.",
        "Tyranitar used Stone Edge. Hydrapple took 88 damage.",
    ]


def test_event_translator_keeps_recoil_and_residual_effects_in_protocol_order():
    translator = PvpEventTranslator()
    translator.observe_snapshot(_damage_snapshot(turn=4))

    steps = translator.translate(
        [
            ["battle", "move", "p1a: Hydrapple", "Leaf Storm", "p2a: Tyranitar"],
            ["battle", "-damage", "p2a: Tyranitar", "49/201"],
            ["battle", "-unboost", "p1a: Hydrapple", "spa", "2"],
            ["battle", "-damage", "p1a: Hydrapple", "199/212", "[from] Recoil"],
            ["battle", "move", "p2a: Tyranitar", "Stone Edge", "p1a: Hydrapple"],
            ["battle", "-damage", "p1a: Hydrapple", "111/212"],
        ]
    )

    assert [step.message for step in steps] == [
        "Hydrapple used Leaf Storm. Tyranitar took 152 damage. "
        "Hydrapple's Sp. Atk fell sharply. Hydrapple took 13 recoil damage.",
        "Tyranitar used Stone Edge. Hydrapple took 88 damage.",
    ]


def test_event_translator_does_not_invent_a_second_action_after_ko():
    translator = PvpEventTranslator()
    translator.observe_snapshot(_damage_snapshot(turn=4))

    steps = translator.translate(
        [
            ["battle", "move", "p1a: Hydrapple", "Leaf Storm", "p2a: Tyranitar"],
            ["battle", "-damage", "p2a: Tyranitar", "0/201"],
            ["battle", "faint", "p2a: Tyranitar"],
        ]
    )

    assert len(steps) == 1
    assert steps[0].message == (
        "Hydrapple used Leaf Storm. Tyranitar took 201 damage. "
        "Tyranitar was knocked out."
    )


def test_event_translator_reports_a_status_that_prevents_action():
    steps = PvpEventTranslator().translate(
        [["battle", "cant", "p2a: Tyranitar", "slp"]]
    )

    assert steps[0].message == "Tyranitar was asleep."
    assert steps[0].event is not None
    assert steps[0].event.status == "slp"


def test_event_translator_keeps_switch_before_response_attack():
    translator = PvpEventTranslator()
    translator.observe_snapshot(_damage_snapshot(turn=4))

    steps = translator.translate(
        [
            ["battle", "switch", "p1a: Hydrapple", "Hydrapple, L50"],
            ["battle", "move", "p2a: Tyranitar", "Stone Edge", "p1a: Hydrapple"],
            ["battle", "-damage", "p1a: Hydrapple", "124/212"],
        ]
    )

    assert [step.message for step in steps] == [
        "Hydrapple entered the battle.",
        "Tyranitar used Stone Edge. Hydrapple took 88 damage.",
    ]
