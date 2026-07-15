from dataclasses import dataclass


@dataclass(frozen=True)
class Variant:
    """
    Represents a cosmetic variant available for a Species.

    A Variant does not modify game rules; it only describes an appearance
    that a Creature can have.
    """

    id: int
    name: str
