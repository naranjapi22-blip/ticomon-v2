from core.evolution.evolution_repository import EvolutionRepository
from core.evolution.evolution_rule import EvolutionRule


class FakeEvolutionRepository(EvolutionRepository):

    def __init__(
        self,
        *rules: EvolutionRule,
    ):
        self._rules = list(rules)

    async def find_options(
        self,
        species_id: int,
    ) -> list[EvolutionRule]:

        return [rule for rule in self._rules if rule.from_species_id == species_id]
