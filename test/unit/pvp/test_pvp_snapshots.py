from __future__ import annotations

from dataclasses import dataclass

from application.pvp.snapshots import snapshot_battle


@dataclass
class FakePokemon:
    species: str
    current_hp: int
    max_hp: int
    current_hp_fraction: float
    status: str | None = None
    fainted: bool = False
    forme: str | None = None


class FakeBattle:
    turn = 4
    force_switch = True
    _opponent_force_switch = False
    finished = False
    won = False
    lost = False

    def __init__(self) -> None:
        self.active_pokemon = FakePokemon("Gyarados", 58, 100, 0.58, "brn")
        self.opponent_active_pokemon = FakePokemon(
            "Arcanine", 0, 100, 0.0, fainted=True
        )
        self.team = {
            "gyarados": self.active_pokemon,
            "pikachu": FakePokemon("Pikachu", 100, 100, 1.0),
        }
        self.opponent_team = {
            "arcanine": self.opponent_active_pokemon,
            "eevee": FakePokemon("Eevee", 100, 100, 1.0),
        }


def test_snapshot_reads_battle_state_and_remaining_teams() -> None:
    snapshot = snapshot_battle(FakeBattle(), player_id=10, opponent_id=20)

    assert snapshot.turn == 4
    assert snapshot.player_active is not None
    assert snapshot.player_active.current_hp == 58
    assert snapshot.player_active.status == "BRN"
    assert snapshot.opponent_active is not None
    assert snapshot.opponent_active.fainted
    assert snapshot.player_remaining == 2
    assert snapshot.opponent_remaining == 1
    assert snapshot.force_switch_player
    assert not snapshot.force_switch_opponent
    assert not snapshot.finished


def test_snapshot_derives_winner_only_from_battle_flags() -> None:
    battle = FakeBattle()
    battle.finished = True
    battle.lost = True

    snapshot = snapshot_battle(battle, player_id=10, opponent_id=20)

    assert snapshot.winner_id == 20
    assert not snapshot.tie
