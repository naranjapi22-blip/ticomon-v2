import asyncio
from collections import Counter

from core.rarity import Rarity
from core.spawn.weighted_selector import WeightedSelector
from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)

SIMULATIONS = 100_000


async def analyze_rarity(
    repository: NeonSpeciesRepository,
    selector: WeightedSelector,
    rarity: Rarity,
) -> None:
    """
    Runs a statistical simulation for a single spawn rarity.
    """

    species = await repository.find_by_spawn_rarity(rarity)

    if not species:
        print(f"\n{rarity.value}: no species found.")
        return

    counter = Counter()

    for _ in range(SIMULATIONS):
        selected = selector.select(
            species,
            amount=1,
        )[0]

        counter[selected.name] += 1

    expected = SIMULATIONS / len(species)

    print()
    print("=" * 70)
    print(f"RARITY: {rarity.value}")
    print("=" * 70)
    print(f"Species: {len(species)}")
    print(f"Simulations: {SIMULATIONS}")
    print(f"Expected per species: {expected:.2f}")

    print("\nMost common")
    print("-" * 70)

    for name, amount in counter.most_common(10):

        deviation = (amount - expected) / expected * 100

        print(f"{name:<25}" f"{amount:>8}" f" ({deviation:+6.2f}%)")

    print("\nLeast common")
    print("-" * 70)

    for name, amount in counter.most_common()[-10:]:

        deviation = (amount - expected) / expected * 100

        print(f"{name:<25}" f"{amount:>8}" f" ({deviation:+6.2f}%)")


async def main():

    repository = NeonSpeciesRepository()
    selector = WeightedSelector()

    for rarity in Rarity:
        await analyze_rarity(
            repository,
            selector,
            rarity,
        )


if __name__ == "__main__":
    asyncio.run(main())
