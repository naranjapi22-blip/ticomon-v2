from core.rarity import Rarity
from core.spawn.rule import Rule
from core.species.species import Species
from core.species.species_repository import SpeciesRepository


class FakeSpeciesRepository(SpeciesRepository):
    def __init__(
        self,
        species: tuple[Species, ...],
    ):
        self._species = species
        self.last_requested_rarity = None

    async def get(
        self,
        species_id: int,
    ) -> Species:
        for species in self._species:
            if species.id == species_id:
                return species

        raise ValueError(f"Species {species_id} not found.")

    async def get_many(
        self,
        species_ids: list[int] | tuple[int, ...],
    ) -> list[Species]:
        return [species for species in self._species if species.id in species_ids]

    async def find_by_name(
        self,
        name: str,
    ) -> Species | None:
        for species in self._species:
            if species.name == name:
                return species

        return None

    async def find_many_by_names(
        self,
        names: list[str] | tuple[str, ...],
    ) -> dict[str, Species]:
        requested = set(names)
        return {
            species.name: species
            for species in self._species
            if species.name in requested
        }

    async def get_all(
        self,
    ) -> tuple[Species, ...]:
        return self._species

    async def find_by_spawn_rarity(
        self,
        rarity: Rarity,
    ) -> tuple[Species, ...]:
        self.last_requested_rarity = rarity

        # This fake does not filter by rarity.
        # It only records which rarity was requested.
        return self._species


class FakeRaritySelector:
    def __init__(self, rarity: Rarity):
        self._rarity = rarity
        self.calls = 0

    def select(self):
        self.calls += 1
        return self._rarity


class FakeRuleEngine:
    def __init__(self):
        self.calls = 0

    def apply(
        self,
        species_pool,
        rules,
        context,
        profile,
    ):
        self.calls += 1
        return species_pool


class FakeWeightedSelector:
    def __init__(self):
        self.calls = 0

    def select(
        self,
        species,
        amount,
    ):
        self.calls += 1
        return species[:amount]


class RejectAllRule(Rule):
    def allows(
        self,
        species,
        context,
        profile,
    ):
        return False
