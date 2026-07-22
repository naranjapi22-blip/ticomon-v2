from core.creature.creature import Creature


def format_creature_entry(
    creature: Creature,
    species_emoji: str | None = None,
) -> str:
    prefix = f"{species_emoji} " if species_emoji else ""
    return (
        f"{prefix}#{creature.collection_number} "
        f"{creature.species.name.title()} — IVs: {creature.iv_percentage}%"
    )


def build_top_title(type_name: str | None) -> str:
    if type_name is None:
        return "Top Pokémon"

    return f"Top {type_name.title()} Pokémon"


def build_recent_title(
    type_name: str | None,
    shiny_only: bool,
) -> str:
    if shiny_only:
        return "✨ Recent Shiny Pokémon"

    if type_name is None:
        return "Recent Pokémon"

    return f"Recent {type_name.title()} Pokémon"


def build_empty_message(
    *,
    type_name: str | None,
    shiny_only: bool,
) -> str:
    if shiny_only:
        return "You do not have any shiny Pokémon."

    if type_name is None:
        return "You do not have any Pokémon yet."

    return f"You do not have any {type_name.title()}-type Pokémon."
