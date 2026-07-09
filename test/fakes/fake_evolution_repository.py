from core.evolution.evolution_repository import EvolutionRepository
from core.evolution.evolution_rule import EvolutionRule


class FakeEvolutionRepository(EvolutionRepository):
    """
    In-memory evolution repository for tests.
    """

    def __init__(
        self,
        *rules: EvolutionRule,
    ) -> None:
        self._rules = {rule.from_species_id: rule for rule in rules}

    async def find_next(
        self,
        species_id: int,
    ) -> EvolutionRule | None:

        return self._rules.get(
            species_id,
        )
