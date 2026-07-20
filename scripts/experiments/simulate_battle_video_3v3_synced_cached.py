from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from core.battle.engine.battle_fighter import BattleFighter
from core.battle.engine.battle_simulator import BattleSimulator
from core.battle.ports.damage_calculator import DamageCalculator, DamageResult
from rendering.battle.assets import BattleAssets
from rendering.battle.video_renderer import render_battle_video


class DemoDamageCalculator(DamageCalculator):
    """Deterministic damage used only by this isolated experiment."""

    def calculate(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
        *,
        random_source,
    ) -> DamageResult:
        damage = 26 if attacker.display_name == "Pikachu" else 21
        return DamageResult(
            damage=damage,
            hit=True,
            critical=False,
            effectiveness_label="",
            message=f"{attacker.display_name} hits {defender.display_name}.",
        )


class DeterministicRandom:
    def randint(self, a: int, b: int) -> int:
        return a

    def random(self) -> float:
        return 0.5

    def sample(self, population: list, k: int) -> list:
        return list(population[:k])


def build_fighter(
    *,
    creature_id: int,
    name: str,
    showdown_id: str,
    pokeapi_id: int,
    pokemon_type: str,
    hp: int,
    speed: int,
    move_id: str,
    move_name: str,
) -> BattleFighter:
    return BattleFighter(
        creature_id=creature_id,
        display_name=name,
        species_showdown_id=showdown_id,
        nature_showdown_id="hardy",
        types=(pokemon_type,),
        hp_max=hp,
        attack=70,
        special_attack=70,
        defense=65,
        special_defense=65,
        speed=speed,
        move_id=move_id,
        move_display_name=move_name,
        pokeapi_id=pokeapi_id,
        is_shiny=False,
    )


def simulate_battle():
    pikachu_moves = (
        ("thunderbolt", "Thunderbolt"),
        ("quickattack", "Quick Attack"),
        ("thunderbolt", "Thunderbolt"),
    )
    charizard_moves = (
        ("flamethrower", "Flamethrower"),
        ("tackle", "Tackle"),
        ("flamethrower", "Flamethrower"),
    )
    pikachu_team = tuple(
        build_fighter(
            creature_id=index,
            name=f"Pikachu {index}",
            showdown_id="pikachu",
            pokeapi_id=25,
            pokemon_type="electric",
            hp=100,
            speed=110,
            move_id=move_id,
            move_name=move_name,
        )
        for index, (move_id, move_name) in enumerate(pikachu_moves, 1)
    )
    charizard_team = tuple(
        build_fighter(
            creature_id=100 + index,
            name=f"Charizard {index}",
            showdown_id="charizard",
            pokeapi_id=6,
            pokemon_type="fire",
            hp=100,
            speed=95,
            move_id=move_id,
            move_name=move_name,
        )
        for index, (move_id, move_name) in enumerate(charizard_moves, 1)
    )
    result = BattleSimulator(
        DemoDamageCalculator(),
        random_source=DeterministicRandom(),
    ).run(
        pikachu_team,
        charizard_team,
        side_a_name="Alice",
        side_b_name="Bob",
        side_a_trainer_id=1,
        side_b_trainer_id=2,
    )
    return result


def encode_video(
    *,
    output_path: Path,
    player_path: Path,
    opponent_path: Path,
    fps: int,
    crf: int,
    battle_id: int,
) -> tuple[float, int, int, int, str]:
    result = simulate_battle()
    return render_battle_video(
        result,
        {
            "Alice": ((25, False),) * 3,
            "Bob": ((6, False),) * 3,
        },
        "Alice",
        "Bob",
        BattleAssets().get_background_for_battle(battle_id),
        output_path,
        fps=fps,
        crf=crf,
        sprite_paths=(player_path, opponent_path),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Isolated experiment: simulate a grouped 3v3 TicoMon battle and "
            "render it with Showdown GIFs only."
        )
    )
    parser.add_argument("--player", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("complete_battle_3v3_synced_cached.mp4"),
    )
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--crf", type=int, default=27)
    parser.add_argument("--battle-id", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.fps <= 0:
        raise SystemExit("--fps must be greater than zero.")
    if not 0 <= args.crf <= 51:
        raise SystemExit("--crf must be between 0 and 51.")

    elapsed, frame_count, step_count, visual_scene_count, winner = encode_video(
        output_path=args.output,
        player_path=args.player,
        opponent_path=args.opponent,
        fps=args.fps,
        crf=args.crf,
        battle_id=args.battle_id,
    )

    output = args.output.resolve()
    size_mb = output.stat().st_size / (1024 * 1024)
    duration = frame_count / args.fps

    print(f"Created: {output}")
    print(f"Winner: {winner}")
    print(f"Battle steps: {step_count}")
    print(f"Visual scenes: {visual_scene_count}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Frames: {frame_count} at {args.fps} FPS")
    print(f"Render time: {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
