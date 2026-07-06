import asyncio
from collections import Counter

from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.spawn_factory import SpawnFactory
from core.spawn.world import World
from infrastructure.species.neon_species_repository import NeonSpeciesRepository


async def main():
    repository = NeonSpeciesRepository()

    spawn_service = SpawnFactory.create(repository)

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
        event=None,
    )

    profile = SpawnProfile(
        opportunity_count=1000,
    )

    opportunities = await spawn_service.spawn(
        context=context,
        profile=profile,
    )

    species_counter = Counter()
    shiny_count = 0

    for opportunity in opportunities:
        species_counter[opportunity.species.name] += 1

        if opportunity.is_shiny:
            shiny_count += 1

    print("=" * 70)
    print(f"Generated opportunities : {len(opportunities)}")
    print(f"Unique species          : {len(species_counter)}")
    print(f"Shiny count             : {shiny_count}")
    print("=" * 70)

    print("\nTop 25 most generated species:\n")

    for species, count in species_counter.most_common(25):
        print(f"{species:<30} {count:>4}")


if __name__ == "__main__":
    asyncio.run(main())
