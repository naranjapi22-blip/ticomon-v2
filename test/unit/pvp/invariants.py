from __future__ import annotations

from application.pvp.snapshots import PvpBattleSnapshot
from rendering.battle.presentation_state import BattlePresentationState


def assert_snapshot_invariants(snapshot: PvpBattleSnapshot) -> None:
    for pokemon in (
        snapshot.player_active,
        snapshot.opponent_active,
        *snapshot.player_team,
        *snapshot.opponent_team,
    ):
        if pokemon is None:
            continue
        if pokemon.current_hp is not None:
            assert 0 <= pokemon.current_hp <= (pokemon.max_hp or pokemon.current_hp)
            assert pokemon.current_hp == 0 or not pokemon.fainted
            assert pokemon.current_hp != 0 or pokemon.fainted
        if pokemon.fainted:
            assert pokemon.status == "FNT"

    assert 0 <= snapshot.player_remaining <= 3
    assert 0 <= snapshot.opponent_remaining <= 3
    if snapshot.player_team:
        assert snapshot.player_remaining == sum(
            not pokemon.fainted for pokemon in snapshot.player_team
        )
    if snapshot.opponent_team:
        assert snapshot.opponent_remaining == sum(
            not pokemon.fainted for pokemon in snapshot.opponent_team
        )
    if snapshot.finished:
        assert snapshot.winner_id is not None or snapshot.tie


def assert_presentation_matches_snapshot(
    presentation: BattlePresentationState, snapshot: PvpBattleSnapshot
) -> None:
    assert presentation.bottom.hp_current == (
        snapshot.player_active.current_hp if snapshot.player_active else 0
    )
    assert presentation.top.hp_current == (
        snapshot.opponent_active.current_hp if snapshot.opponent_active else 0
    )
    assert presentation.bottom.remaining == snapshot.player_remaining
    assert presentation.top.remaining == snapshot.opponent_remaining
    assert presentation.last_decisive_event == snapshot.last_decisive_event
    assert presentation.last_decisive_event_turn == snapshot.last_decisive_event_turn
