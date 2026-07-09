from dataclasses import dataclass

from core.candy.candy_amount import CandyAmount
from core.species.species import Species


@dataclass(frozen=True, slots=True)
class EvolutionConfirmation:
    previous_species: Species
    evolved_species: Species
    cost: CandyAmount
    current_candies: int
