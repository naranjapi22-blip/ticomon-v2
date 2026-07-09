from core.candy.candy_type import CandyType
from core.evolution.evolution_rule import EvolutionRule


class EvolutionMapper:
    """
    Maps database evolution rows into domain objects.
    """

    def from_row(
        self,
        row,
    ) -> EvolutionRule:

        return EvolutionRule(
            from_species_id=row["from_species_id"],
            to_species_id=row["to_species_id"],
            candy_type=CandyType(
                row["candy_type"],
            ),
            tier=row["tier"],
        )
