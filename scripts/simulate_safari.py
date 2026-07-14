from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulation.safari import (  # noqa: E402
    CatalogSource,
    SafariSimulationConfig,
    SafariSimulationRunner,
)
from simulation.safari.report import render_console_report  # noqa: E402


def _parse_int_list(raw: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in raw.split(",") if item.strip())


def _parse_strategy_list(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Safari balance simulations.")
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--levels", type=_parse_int_list, default=(1, 2, 3, 4, 5))
    parser.add_argument("--participants", type=_parse_int_list, default=(2, 4, 6, 10))
    parser.add_argument(
        "--strategies",
        type=_parse_strategy_list,
        default=(
            "conservative",
            "aggressive",
            "random",
            "fixed_1",
            "fixed_2",
            "fixed_3",
        ),
    )
    parser.add_argument(
        "--species-source",
        choices=[source.value for source in CatalogSource],
        default=CatalogSource.AUTO.value,
    )
    parser.add_argument("--global-shiny-chance", type=float, default=0.001)
    parser.add_argument("--progress-interval", type=int, default=10_000)
    parser.add_argument("--output", type=Path)
    return parser


async def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = SafariSimulationConfig(
        simulations=args.simulations,
        levels=args.levels,
        participant_counts=args.participants,
        strategy_names=args.strategies,
        seed=args.seed,
        global_shiny_chance=args.global_shiny_chance,
        species_source=CatalogSource(args.species_source),
    )
    total_scenarios = (
        len(config.levels) * len(config.participant_counts) * len(config.strategy_names)
    )
    completed_scenarios = 0

    def progress_callback(
        completed: int,
        total: int,
        strategy_name: str,
        level: int,
        participant_count: int,
    ) -> None:
        if (
            completed == total
            or args.progress_interval <= 0
            or completed % args.progress_interval == 0
        ):
            print(
                f"{completed:,} / {total:,} completed "
                f"(level={level}, participants={participant_count}, "
                f"strategy={strategy_name})",
                flush=True,
            )

    def scenario_progress_callback(
        completed: int,
        total: int,
        strategy_name: str,
        level: int,
        participant_count: int,
    ) -> None:
        nonlocal completed_scenarios
        progress_callback(completed, total, strategy_name, level, participant_count)
        if completed == total:
            completed_scenarios += 1
            print(
                f"scenario {completed_scenarios:,} / {total_scenarios:,} complete",
                flush=True,
            )

    report = await SafariSimulationRunner(config).run(
        progress_callback=scenario_progress_callback,
    )
    print(render_console_report(report))
    if args.output is not None:
        args.output.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
