from core.spawn.application.spawn_service import SpawnService
from core.spawn.rule_engine import RuleEngine
from core.spawn.species_selector import SpeciesSelector
from core.spawn.weighted_selector import WeightedSelector
from core.species.species_repository import SpeciesRepository


class SpawnFactory:
    """
    Builds the Spawn Engine.
    """

    @staticmethod
    def create(
        repository: SpeciesRepository,
    ) -> SpawnService:
        selector = SpeciesSelector(
            repository=repository,
            rule_engine=RuleEngine(),
            weighted_selector=WeightedSelector(),
        )

        return SpawnService(selector)
