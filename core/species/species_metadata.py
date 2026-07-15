from dataclasses import dataclass


@dataclass(frozen=True)
class SpeciesMetadata:
    """
    Descriptive information about a species used by game rules.

    Does not represent species statistics or behavior.
    """

    generation: int
    is_baby: bool
    is_legendary: bool
    is_mythical: bool
