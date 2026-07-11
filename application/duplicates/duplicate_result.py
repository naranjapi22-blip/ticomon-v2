from dataclasses import dataclass


@dataclass(frozen=True)
class DuplicateSpeciesResult:
    species_id: int
    species_name: str
    amount: int
