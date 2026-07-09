from core.evolution.evolution_chain import EvolutionChain


class EvolutionBuilder:
    """
    Builder for creating EvolutionChain instances in tests.
    """

    def __init__(self):
        self._id = 1
        self._species = [1, 2]
        self._candy_requirements = {
            1: 25,
        }

    def with_id(
        self,
        chain_id: int,
    ):
        self._id = chain_id
        return self

    def with_species(
        self,
        species: list[int],
    ):
        self._species = species
        return self

    def with_candy_cost(
        self,
        species_id: int,
        amount: int,
    ):
        self._candy_requirements[species_id] = amount
        return self

    def build(self) -> EvolutionChain:
        return EvolutionChain(
            id=self._id,
            species=self._species,
            candy_requirements=self._candy_requirements,
        )
