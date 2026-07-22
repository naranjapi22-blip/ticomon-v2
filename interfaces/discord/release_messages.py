from application.release.exceptions import ReleaseCreatureAssignedToTeam


async def assigned_creatures_message(
    core,
    trainer_id: int,
    error: ReleaseCreatureAssignedToTeam,
) -> str:
    creatures = await core.creature_repository.get_by_collection_numbers(
        trainer_id,
        error.collection_numbers,
    )
    names_by_number = {
        creature.collection_number: creature.species.name.title()
        for creature in creatures
    }
    assigned = "\n".join(
        f"• #{number} {names_by_number.get(number, 'Pokémon')}"
        for number in error.collection_numbers
    )
    return (
        "❌ These Pokémon are currently assigned to your team and "
        "cannot be released:\n\n"
        f"{assigned}\n\n"
        "Remove or replace them in your team before trying again."
    )
