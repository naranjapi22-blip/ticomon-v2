from dataclasses import dataclass

from application.creature.creature_info_service import (
    CreatureInfoService,
)
from application.evolution.evolution_application_service import (
    EvolutionApplicationService,
)
from application.pokedex.pokedex_service import PokedexService
from application.profile.profile_service import ProfileService
from application.species_info.species_info_service import (
    SpeciesInfoService,
)
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_service import (
    CaptureApplicationService,
)
from core.capture.domain.capture_ball_selector import CaptureBallSelector
from core.capture.domain.capture_chance_calculator import (
    CaptureChanceCalculator,
)
from core.capture.service import CaptureService
from core.evolution.evolution_cost_policy import (
    EvolutionCostPolicy,
)
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_service import EvolutionService
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
from core.stats.stat_calculator import StatCalculator
from infrastructure.evolution.neon_evolution_repository import (
    NeonEvolutionRepository,
)
from infrastructure.persistence.repositories.neon_candy_repository import (
    NeonCandyRepository,
)
from infrastructure.persistence.repositories.neon_creature_repository import (
    NeonCreatureRepository,
)
from infrastructure.persistence.repositories.neon_profile_repository import (
    NeonProfileRepository,
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
    candy_repository: NeonCandyRepository

    spawn_session_repository: InMemorySpawnSessionRepository

    stat_calculator: StatCalculator

    spawn_application: SpawnApplicationService
    select_opportunity_application: SelectOpportunityApplicationService
    get_current_spawn_application: GetCurrentSpawnApplicationService
    capture_application: CaptureApplicationService
    evolution_application: EvolutionApplicationService

    profile_service: ProfileService
    creature_info_service: CreatureInfoService
    species_info_service: SpeciesInfoService
    pokedex_service: PokedexService


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

    candy_repository = NeonCandyRepository()
    evolution_repository = NeonEvolutionRepository()
    reward_policy = RewardPolicy()

    creature_info_service = CreatureInfoService(
        creature_repository=creature_repository,
    )

    species_info_service = SpeciesInfoService(
        species_repository=species_repository,
        creature_repository=creature_repository,
    )

    profile_repository = NeonProfileRepository()

    spawn_session_repository = InMemorySpawnSessionRepository()

    stat_calculator = StatCalculator()

    chance_calculator = chance_calculator or CaptureChanceCalculator()

    ball_selector = ball_selector or CaptureBallSelector()

    capture_application = CaptureApplicationService(
        capture_service=CaptureService(
            chance_calculator=chance_calculator,
            ball_selector=ball_selector,
        ),
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        reward_policy=reward_policy,
        spawn_session_repository=spawn_session_repository,
    )

    evolution_application = EvolutionApplicationService(
        evolution_service=EvolutionService(
            policy=EvolutionPolicy(
                cost_policy=EvolutionCostPolicy(),
            ),
            species_repository=species_repository,
        ),
        evolution_repository=evolution_repository,
        creature_repository=creature_repository,
        candy_repository=candy_repository,
    )

    profile_service = ProfileService(
        creature_repository=creature_repository,
        profile_repository=profile_repository,
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

    pokedex_service = PokedexService(
        species_repository=species_repository,
        creature_repository=creature_repository,
    )

    return CoreServices(
        species_repository=species_repository,
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        spawn_session_repository=spawn_session_repository,
        stat_calculator=stat_calculator,
        spawn_application=spawn_application,
        select_opportunity_application=select_opportunity_application,
        get_current_spawn_application=get_current_spawn_application,
        capture_application=capture_application,
        evolution_application=evolution_application,
        profile_service=profile_service,
        creature_info_service=creature_info_service,
        species_info_service=species_info_service,
        pokedex_service=pokedex_service,
    )
