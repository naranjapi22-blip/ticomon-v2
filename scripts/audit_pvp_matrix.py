"""Run the deterministic PvP protocol audit matrix without external services."""

# The matrix is intentionally written as compact protocol fixtures.
# ruff: noqa: E501

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from application.pvp.events import PvpEventTranslator
from application.pvp.snapshots import PvpBattleSnapshot, PvpPokemonSnapshot


def _snapshot(target_hp: int = 100) -> PvpBattleSnapshot:
    return PvpBattleSnapshot(
        turn=10,
        player_id=1,
        opponent_id=2,
        player_active=PvpPokemonSnapshot("Pikachu", None, 100, 100, 1.0, None, False),
        opponent_active=PvpPokemonSnapshot(
            "Blissey", None, target_hp, 100, target_hp / 100, None, False
        ),
        player_remaining=3,
        opponent_remaining=3,
        force_switch_player=False,
        force_switch_opponent=False,
        finished=False,
        winner_id=None,
        tie=False,
    )


def _run(name: str, messages: list[list[str]], expected: str, *, hp=100) -> None:
    translator = PvpEventTranslator(player_id=1, opponent_id=2)
    translator.observe_snapshot(_snapshot(hp))
    steps = translator.translate(messages)
    rendered = " ".join(step.message for step in steps)
    assert expected in rendered, f"{name}: {expected!r} not in {rendered!r}"
    event = steps[-1].event if steps else None
    event_text = event.move_name if event else None
    print(
        f"{name}: source=canonical protocol={len(messages)} "
        f"snapshot=turn10 Pikachu={100}/100 Blissey={hp}/100 "
        f"remaining=3/3 event={event_text!r} phase=ACTIVE public={rendered}"
    )


def main() -> None:
    # fmt: off
    cases = [
        (
            "physical",
            [
                ["battle", "move", "p1a: Pikachu", "Tackle"],
                ["battle", "-damage", "p2a: Blissey", "80/100"],
            ],
            "20 damage",
        ),
        (
            "special",
            [
                ["battle", "move", "p1a: Pikachu", "Thunderbolt"],
                ["battle", "-damage", "p2a: Blissey", "80/100"],
            ],
            "20 damage",
        ),
        (
            "super_effective",
            [["battle", "-supereffective", "p2a: Blissey"]],
            "super effective",
        ),
        (
            "not_very_effective",
            [["battle", "-resisted", "p2a: Blissey"]],
            "not very effective",
        ),
        ("immune", [["battle", "-immune", "p2a: Blissey"]], "was immune"),
        ("critical", [["battle", "-crit", "p2a: Blissey"]], "critical hit"),
        ("miss", [["battle", "-miss", "p2a: Blissey"]], "missed"),
        ("fail", [["battle", "-fail", "p2a: Blissey"]], "failed"),
        (
            "no_damage_move",
            [["battle", "move", "p1a: Pikachu", "Swords Dance"]],
            "used Swords Dance",
        ),
        ("recovery", [["battle", "-heal", "p1a: Pikachu", "100/100"]], "recovered HP"),
        (
            "variable_damage",
            [["battle", "-damage", "p2a: Blissey", "73/100"]],
            "27 damage",
        ),
        (
            "direct_ko",
            [
                ["battle", "move", "p1a: Pikachu", "Tackle"],
                ["battle", "-damage", "p2a: Blissey", "0/100"],
                ["battle", "faint", "p2a: Blissey"],
            ],
            "was knocked out",
        ),
        ("boost_1", [["battle", "-boost", "p1a: Pikachu", "atk", "1"]], "Attack rose"),
        (
            "boost_2",
            [["battle", "-boost", "p1a: Pikachu", "atk", "2"]],
            "Attack rose sharply",
        ),
        (
            "unboost_1",
            [["battle", "-unboost", "p1a: Pikachu", "def", "1"]],
            "Defense fell",
        ),
        (
            "unboost_2",
            [["battle", "-unboost", "p1a: Pikachu", "def", "2"]],
            "Defense fell sharply",
        ),
        (
            "multiple_stats",
            [
                ["battle", "-boost", "p1a: Pikachu", "atk", "1"],
                ["battle", "-boost", "p1a: Pikachu", "spe", "1"],
            ],
            "Speed rose",
        ),
        (
            "draco_meteor",
            [["battle", "-unboost", "p1a: Pikachu", "spa", "2"]],
            "Sp. Atk fell sharply",
        ),
        (
            "close_combat",
            [
                ["battle", "-unboost", "p1a: Pikachu", "def", "1"],
                ["battle", "-unboost", "p1a: Pikachu", "spd", "1"],
            ],
            "Sp. Def fell",
        ),
        (
            "superpower",
            [
                ["battle", "-unboost", "p1a: Pikachu", "atk", "1"],
                ["battle", "-unboost", "p1a: Pikachu", "def", "1"],
            ],
            "Defense fell",
        ),
        (
            "sandstorm",
            [
                ["battle", "-weather", "Sandstorm"],
                ["battle", "-damage", "p2a: Blissey", "88/100", "[from] Sandstorm"],
            ],
            "Sandstorm dealt 12 damage",
        ),
        (
            "poison",
            [["battle", "-damage", "p2a: Blissey", "88/100", "[from] psn"]],
            "poison damage",
        ),
        (
            "toxic",
            [["battle", "-damage", "p2a: Blissey", "88/100", "[from] tox"]],
            "poison damage",
        ),
        (
            "burn",
            [["battle", "-damage", "p2a: Blissey", "88/100", "[from] brn"]],
            "burn damage",
        ),
        (
            "recoil",
            [["battle", "-damage", "p1a: Pikachu", "88/100", "[from] Recoil"]],
            "recoil damage",
        ),
        ("hazard", [["battle", "-fieldstart", "Spikes"]], "field changed"),
        (
            "life_orb",
            [["battle", "-damage", "p1a: Pikachu", "88/100", "[from] Life Orb"]],
            "item damage",
        ),
        ("ability", [["battle", "-ability", "p2a: Blissey", "Pressure"]], "activated"),
        (
            "leech_seed",
            [["battle", "-damage", "p2a: Blissey", "88/100", "[from] Leech Seed"]],
            "leech seed damage",
        ),
        (
            "confusion",
            [["battle", "-damage", "p1a: Pikachu", "88/100", "[from] confusion"]],
            "confusion damage",
        ),
        (
            "unknown_cause",
            [["battle", "-damage", "p2a: Blissey", "88/100", "[from] strange effect"]],
            "indirect damage",
        ),
        ("status_par", [["battle", "-status", "p2a: Blissey", "par"]], "PAR"),
        ("status_burn", [["battle", "-status", "p2a: Blissey", "brn"]], "BRN"),
        ("status_poison", [["battle", "-status", "p2a: Blissey", "psn"]], "PSN"),
        ("status_toxic", [["battle", "-status", "p2a: Blissey", "tox"]], "TOX"),
        ("status_sleep", [["battle", "-status", "p2a: Blissey", "slp"]], "SLP"),
        ("status_freeze", [["battle", "-status", "p2a: Blissey", "frz"]], "FRZ"),
        ("status_cure", [["battle", "-curestatus", "p2a: Blissey", "brn"]], "cured"),
        (
            "voluntary_switch",
            [["battle", "switch", "p1a: Pikachu", "Raichu, L50"]],
            "entered the battle",
        ),
        (
            "forced_switch",
            [
                ["battle", "faint", "p2a: Blissey"],
                ["battle", "switch", "p2a: Gengar", "Gengar, L50"],
            ],
            "entered the battle",
        ),
        ("win_initiator", [["battle", "win", "Orange"]], "won the battle"),
        ("win_rival", [["battle", "win", "Jorroco"]], "won the battle"),
        ("tie", [["battle", "tie"]], "tie"),
    ]
    # fmt: on
    for name, messages, expected in cases:
        _run(name, messages, expected, hp=212 if name == "direct_ko" else 100)
    print(f"matrix: {len(cases)} deterministic protocol scenarios passed")


if __name__ == "__main__":
    main()
