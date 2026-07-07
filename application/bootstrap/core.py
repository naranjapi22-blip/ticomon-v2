from dataclasses import dataclass

from core.capture.application.capture_service import (
    CaptureApplicationService,
)
from core.capture.domain.capture_ball_selector import CaptureBallSelector
from core.capture.domain.capture_chance_calculator import (
    CaptureChanceCalculator,
)
from core.capture.service import CaptureService
from core.spawn.application.spawn_service import SpawnService
from core.spawn.rarity_selector import RaritySelector
from core.spawn.rule_engine import RuleEngine
from core.spawn.species_selector import SpeciesSelector
from core.spawn.weighted_selector import WeightedSelector
from infrastructure.persistence.repositories.neon_creature_repository import (
    NeonCreatureRepository,
)
from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)


@dataclass(frozen=True, slots=True)
class CoreServices:
    """
    Root object containing every service required
    to execute the Core.
    """

    species_repository: NeonSpeciesRepository
    creature_repository: NeonCreatureRepository

    spawn_service: SpawnService

    capture_application: CaptureApplicationService


def build_core() -> CoreServices:
    """
    Builds the complete Core dependency graph.
    """

    species_repository = NeonSpeciesRepository()

    creature_repository = NeonCreatureRepository(
        species_repository=species_repository,
    )

    capture_application = CaptureApplicationService(
        capture_service=CaptureService(
            chance_calculator=CaptureChanceCalculator(),
            ball_selector=CaptureBallSelector(),
        ),
        creature_repository=creature_repository,
    )

    selector = SpeciesSelector(
        repository=species_repository,
        rarity_selector=RaritySelector(),
        rule_engine=RuleEngine(),
        weighted_selector=WeightedSelector(),
    )

    spawn_service = SpawnService(
        selector=selector,
    )

    return CoreServices(
        species_repository=species_repository,
        creature_repository=creature_repository,
        spawn_service=spawn_service,
        capture_application=capture_application,
    )
