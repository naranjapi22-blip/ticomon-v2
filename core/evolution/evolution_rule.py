from dataclasses import dataclass

from core.candy.candy_type import CandyType


@dataclass(frozen=True)
class EvolutionRule:
    """
    Represents a valid evolution transition.
    """

    from_species_id: int

    to_species_id: int

    candy_type: CandyType

    tier: str
