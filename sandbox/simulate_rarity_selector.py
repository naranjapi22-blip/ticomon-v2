# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collections import Counter

from core.spawn.rarity_selector import RaritySelector

SIMULATIONS = 100_000


def main():

    selector = RaritySelector()

    results = Counter()

    for _ in range(SIMULATIONS):
        rarity = selector.select()
        results[rarity] += 1

    print()
    print(f"Simulations: {SIMULATIONS}")
    print()

    for rarity, amount in results.items():
        percentage = amount / SIMULATIONS * 100

        print(f"{rarity.value:<15}" f"{amount:>8}" f" ({percentage:6.2f}%)")


if __name__ == "__main__":
    main()
