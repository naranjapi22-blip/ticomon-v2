from dataclasses import dataclass

from core.capture.application.capture_service import (
    CaptureApplicationService,
)
from core.capture.domain.capture_ball_selector import CaptureBallSelector
from core.capture.domain.capture_chance_calculator import (
    CaptureChanceCalculator,
)
from core.capture.service import CaptureService
from core.spawn.application.get_current_spawn_application_service import (
    GetCurrentSpawnApplicationService,
)
from core.spawn.application.select_opportunity_application_service import (
    SelectOpportunityApplicationService,
)
from core.spawn.application.spawn_application_service import (
    SpawnApplicationService,
)
from core.spawn.application.spawn_service import SpawnService
from core.spawn.rarity_selector import RaritySelector
from core.spawn.rule_engine import RuleEngine
from core.spawn.species_selector import SpeciesSelector
from core.spawn.weighted_selector import WeightedSelector
from infrastructure.persistence.repositories.neon_creature_repository import (
    NeonCreatureRepository,
)
from infrastructure.spawn.in_memory_spawn_session_repository import (
    InMemorySpawnSessionRepository,
)
from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)


@dataclass(frozen=True, slots=True)
class CoreServices:
    species_repository: NeonSpeciesRepository
    creature_repository: NeonCreatureRepository

    spawn_session_repository: InMemorySpawnSessionRepository

    spawn_application: SpawnApplicationService
    select_opportunity_application: SelectOpportunityApplicationService
    get_current_spawn_application: GetCurrentSpawnApplicationService
    capture_application: CaptureApplicationService


def build_core(
    *,
    chance_calculator: CaptureChanceCalculator | None = None,
    ball_selector: CaptureBallSelector | None = None,
) -> CoreServices:
    """
    Builds the complete Core dependency graph.
    """

    species_repository = NeonSpeciesRepository()

    creature_repository = NeonCreatureRepository(
        species_repository=species_repository,
    )

    spawn_session_repository = InMemorySpawnSessionRepository()

    chance_calculator = chance_calculator or CaptureChanceCalculator()

    ball_selector = ball_selector or CaptureBallSelector()

    capture_application = CaptureApplicationService(
        capture_service=CaptureService(
            chance_calculator=chance_calculator,
            ball_selector=ball_selector,
        ),
        creature_repository=creature_repository,
        spawn_session_repository=spawn_session_repository,
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

    spawn_application = SpawnApplicationService(
        spawn_service=spawn_service,
        spawn_session_repository=spawn_session_repository,
    )

    select_opportunity_application = SelectOpportunityApplicationService(
        spawn_session_repository=spawn_session_repository,
    )
    get_current_spawn_application = GetCurrentSpawnApplicationService(
        spawn_session_repository=spawn_session_repository,
    )
    return CoreServices(
        species_repository=species_repository,
        creature_repository=creature_repository,
        spawn_session_repository=spawn_session_repository,
        spawn_application=spawn_application,
        select_opportunity_application=select_opportunity_application,
        get_current_spawn_application=get_current_spawn_application,
        capture_application=capture_application,
    )
