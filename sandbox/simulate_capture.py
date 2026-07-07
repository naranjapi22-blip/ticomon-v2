import asyncio

from application.bootstrap.core import build_core


async def main() -> None:
    services = build_core()

    opportunities = await services.spawn_application.spawn()

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

    attempt_number = 1

    while True:
        result = await services.capture_application.capture(
            trainer_id=123456789012345678,
            opportunity=selected,
        )

        print(f"\n----- Attempt #{attempt_number} -----")
        print(f"Ball: {result.attempt.capture_ball.name}")
        print(f"Chance: {result.attempt.chance * 100:.2f}%")
        print(f"Failed Attempts: {selected.failed_attempts}")

        if result.success:
            assert result.creature is not None

            print("\n✅ Capture successful!\n")

            print(f"ID: {result.creature.id}")
            print(f"Collection #: {result.creature.collection_number}")
            print(f"Species: {result.creature.species.name}")
            print(f"Nature: {result.creature.nature.name}")
            print(f"Shiny: {result.creature.is_shiny}")
            print(f"Attempts: {attempt_number}")

            break

        print("❌ Capture failed!")

        attempt_number += 1


if __name__ == "__main__":
    asyncio.run(main())
