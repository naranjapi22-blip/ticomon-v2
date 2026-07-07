from core.spawn.rule import Rule
from core.spawn.spawn_rarity import SpawnRarity
from core.species.species import Species
from core.species.species_repository import SpeciesRepository


class FakeSpeciesRepository(SpeciesRepository):
    def __init__(self, species: tuple[Species, ...]):
        self._species = species
        self.last_requested_rarity = None

    async def get(self, species_id: int) -> Species:
        raise NotImplementedError

    async def find_by_name(self, name: str):
        raise NotImplementedError

    async def get_all(self):
        return self._species

    async def find_by_spawn_rarity(
        self,
        rarity: SpawnRarity,
    ) -> tuple[Species, ...]:
        self.last_requested_rarity = rarity
        return self._species


class FakeRaritySelector:
    def __init__(self, rarity: SpawnRarity):
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
