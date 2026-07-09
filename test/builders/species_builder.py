from core.creature.base_stats import BaseStats
from core.evolution.evolution_chain import EvolutionChain
from core.rarity import Rarity
from core.species.species import Species
from core.species.species_metadata import SpeciesMetadata


class SpeciesBuilder:
    """
    Builder for creating Species instances in tests.
    """

    def __init__(self):
        self._id = 1
        self._name = "Test Species"
        self._types = ["fire"]
        self._evolution_chain = EvolutionChain(
            id=1,
            species=[1, 2],
            candy_requirements={
                1: 25,
            },
        )

    def with_id(
        self,
        species_id: int,
    ):
        self._id = species_id
        return self

    def with_name(
        self,
        name: str,
    ):
        self._name = name
        return self

    def with_types(
        self,
        types: list[str],
    ):
        self._types = types
        return self

    def with_evolution_chain(
        self,
        chain: EvolutionChain | None,
    ):
        self._evolution_chain = chain
        return self

    def build(self) -> Species:

        return Species(
            id=self._id,
            name=self._name,
            types=self._types,
            base_stats=BaseStats(
                hp=45,
                attack=49,
                defense=49,
                special_attack=65,
                special_defense=65,
                speed=45,
            ),
            height=7,
            weight=69,
            capture_rate=45,
            spawn_rarity=Rarity.COMMON,
            metadata=SpeciesMetadata(
                generation=1,
                is_baby=False,
                is_legendary=False,
                is_mythical=False,
            ),
            evolution_chain=self._evolution_chain,
        )
