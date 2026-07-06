import asyncio

from core.spawn.application.spawn_service import SpawnService
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.rarity_selector import RaritySelector
from core.spawn.region import Region
from core.spawn.rule_engine import RuleEngine
from core.spawn.species_selector import SpeciesSelector
from core.spawn.weighted_selector import WeightedSelector
from core.spawn.world import World
from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)


async def main() -> None:
    species_repository = NeonSpeciesRepository()

    selector = SpeciesSelector(
        repository=species_repository,
        rarity_selector=RaritySelector(),
        rule_engine=RuleEngine(),
        weighted_selector=WeightedSelector(),
    )

    spawn_service = SpawnService(
        selector=selector,
    )

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    profile = SpawnProfile(
        opportunity_count=3,
    )

    opportunities = await spawn_service.spawn(
        context=context,
        profile=profile,
    )

    print("\n========== SPAWN ==========\n")

    for index, opportunity in enumerate(opportunities, start=1):
        print(
            f"[{index}] "
            f"{opportunity.species.name:<15}"
            f"{opportunity.species.spawn_rarity.name}"
        )


if __name__ == "__main__":
    asyncio.run(main())
