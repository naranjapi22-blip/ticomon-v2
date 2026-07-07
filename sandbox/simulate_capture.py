import asyncio

from application.bootstrap.core import build_core
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.world import World


async def main() -> None:
    services = build_core()

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
    )

    profile = SpawnProfile(
        opportunity_count=3,
    )

    opportunities = await services.spawn_service.spawn(
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

    result = await services.capture_application.capture(
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
