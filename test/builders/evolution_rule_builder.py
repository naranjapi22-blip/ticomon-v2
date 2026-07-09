from core.candy.candy_type import CandyType
from core.evolution.evolution_rule import EvolutionRule


class EvolutionRuleBuilder:
    """
    Builder for EvolutionRule tests.
    """

    def __init__(self):
        self._from_species_id = 1
        self._to_species_id = 2
        self._candy_type = CandyType.FIRE
        self._tier = "basic"

    def with_from_species(
        self,
        species_id: int,
    ):
        self._from_species_id = species_id
        return self

    def with_to_species(
        self,
        species_id: int,
    ):
        self._to_species_id = species_id
        return self

    def with_candy_type(
        self,
        candy_type: CandyType,
    ):
        self._candy_type = candy_type
        return self

    def with_tier(
        self,
        tier: str,
    ):
        self._tier = tier
        return self

    def build(self) -> EvolutionRule:
        return EvolutionRule(
            from_species_id=self._from_species_id,
            to_species_id=self._to_species_id,
            candy_type=self._candy_type,
            tier=self._tier,
        )
