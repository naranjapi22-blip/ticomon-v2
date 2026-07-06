import asyncio

from core.capture.application.capture_service import (
    CaptureApplicationService,
)
from core.capture.service import CaptureService
from core.spawn.application.spawn_service import SpawnService
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.rarity_selector import RaritySelector
from core.spawn.region import Region
from core.spawn.rule_engine import RuleEngine
from core.spawn.species_selector import SpeciesSelector
from core.spawn.weighted_selector import WeightedSelector
from core.spawn.world import World
from infrastructure.persistence.repositories.neon_creature_repository import (
    NeonCreatureRepository,
)
from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)


async def main() -> None:
    species_repository = NeonSpeciesRepository()

    creature_repository = NeonCreatureRepository(
        species_repository=species_repository,
    )

    capture_application = CaptureApplicationService(
        capture_service=CaptureService(),
        creature_repository=creature_repository,
    )

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

    selected = opportunities[0]

    print("\n========== CAPTURE ==========\n")
    print(f"Selected: {selected.species.name}")

    result = await capture_application.capture(
        trainer_id=123456789012345678,
        opportunity=selected,
    )

    if not result.success:
        print("\nCapture failed!")
        return

    assert result.creature is not None

    print("\nCapture successful!\n")

    print(f"ID: {result.creature.id}")
    print(f"Collection #: {result.creature.collection_number}")
    print(f"Species: {result.creature.species.name}")
    print(f"Nature: {result.creature.nature.name}")
    print(f"Shiny: {result.creature.is_shiny}")


if __name__ == "__main__":
    asyncio.run(main())
