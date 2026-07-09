import asyncio

from application.bootstrap.core import build_core

GUILD_ID = 123456789
TRAINER_ID = 987654321


async def main() -> None:
    services = build_core()

    session = await services.spawn_application.spawn(
        guild_id=GUILD_ID,
        owner_id=TRAINER_ID,
    )

    print("\n========== SPAWN ==========\n")

    for index, opportunity in enumerate(
        session.opportunities,
        start=1,
    ):
        print(
            f"[{index}] "
            f"{opportunity.species.name:<15}"
            f"{opportunity.species.spawn_rarity.name}"
        )

    selected = await services.select_opportunity_application.select_opportunity(
        guild_id=GUILD_ID,
        opportunity_index=0,
    )

    print("\n========== CAPTURE ==========\n")
    print(f"Selected: {selected.species.name}")

    attempt_number = 1

    while True:

        result = await services.capture_application.capture(
            trainer_id=TRAINER_ID,
            guild_id=GUILD_ID,
        )

        print(f"\n----- Attempt #{attempt_number} -----")
        print(f"Ball: {result.attempt.capture_ball.name}")
        print(f"Chance: {result.attempt.chance * 100:.2f}%")

        if result.success:
            assert result.creature is not None

            print("\n✅ Capture successful!\n")

            print(f"ID: {result.creature.id}")
            print(f"Collection #: {result.creature.collection_number}")
            print(f"Species: {result.creature.species.name}")
            print(f"Nature: {result.creature.nature.name}")
            print(f"Shiny: {result.creature.is_shiny}")

            print("\nCandies:")

            for candy_type, amount in result.reward.items():
                print(f"  {candy_type.value.title()}: +{amount}")

            break

        print("❌ Capture failed!")

        attempt_number += 1


if __name__ == "__main__":
    asyncio.run(main())
