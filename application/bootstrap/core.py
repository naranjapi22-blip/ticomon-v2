import logging
import random
from dataclasses import dataclass

from application.adventure.start_adventure.start_adventure_application_service import (
    StartAdventureApplicationService,
)
from application.creature.creature_collection_service import (
    CreatureCollectionService,
)
from application.creature.creature_info_service import (
    CreatureInfoService,
)
from application.duplicates.duplicate_application_service import (
    DuplicateApplicationService,
)
from application.evolution.evolution_application_service import (
    EvolutionApplicationService,
)
from application.pokedex.pokedex_service import PokedexService
from application.profile.profile_service import ProfileService
from application.release.preview_release_application_service import (
    PreviewReleaseApplicationService,
)
from application.release.release_application_service import (
    ReleaseApplicationService,
)
from application.safari import (
    FinishSafariApplicationService,
    SafariCaptureApplicationService,
    SafariRegistrationApplicationService,
    SafariRouteApplicationService,
    StartSafariApplicationService,
)
from application.species_info.species_info_service import (
    SpeciesInfoService,
)
from application.trade.trade_application_service import (
    TradeApplicationService,
)
from application.trade.trade_display_service import (
    TradeDisplayService,
)
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_service import (
    CaptureApplicationService,
)
from core.capture.attempt_service import CaptureAttemptService
from core.capture.domain.capture_ball_selector import CaptureBallSelector
from core.capture.domain.capture_chance_calculator import (
    CaptureChanceCalculator,
)
from core.capture.service import CaptureService
from core.energy.service import EnergyService
from core.evolution.evolution_cost_policy import (
    EvolutionCostPolicy,
)
from core.evolution.evolution_policy import EvolutionPolicy
from core.evolution.evolution_service import EvolutionService
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari.capture_resolution import SafariCaptureResolver
from core.safari.encounter_generator import SafariEncounterGenerator
from core.safari.map_selector import SafariMapSelector
from core.safari.progress_service import SafariWorldProgressService
from core.safari.route_option_factory import SafariRouteOptionFactory
from core.safari.time_of_day_selector import SafariTimeOfDaySelector
from core.safari.weather_selector import SafariWeatherSelector
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
from infrastructure.persistence.repositories.neon_capture_unit_of_work import (
    NeonCaptureUnitOfWork,
)
from infrastructure.persistence.repositories.neon_creature_repository import (
    NeonCreatureRepository,
)
from infrastructure.persistence.repositories.neon_profile_repository import (
    NeonProfileRepository,
)
from infrastructure.persistence.repositories.neon_trade_repository import (
    NeonTradeRepository,
)
from infrastructure.postgres.energy.neon_energy_repository import (
    NeonEnergyRepository,
)
from infrastructure.postgres.trainer.neon_trainer_repository import (
    NeonTrainerRepository,
)
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from infrastructure.safari.neon_safari_unlock_repository import (
    NeonSafariUnlockRepository,
)
from infrastructure.spawn.in_memory_spawn_session_repository import (
    InMemorySpawnSessionRepository,
)
from infrastructure.species.neon_species_repository import (
    NeonSpeciesRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CoreServices:
    species_repository: NeonSpeciesRepository
    creature_repository: NeonCreatureRepository
    trainer_repository: NeonTrainerRepository
    candy_repository: NeonCandyRepository

    spawn_session_repository: InMemorySpawnSessionRepository

    stat_calculator: StatCalculator

    spawn_application: SpawnApplicationService
    select_opportunity_application: SelectOpportunityApplicationService
    get_current_spawn_application: GetCurrentSpawnApplicationService
    capture_application: CaptureApplicationService
    safari_registration_application: SafariRegistrationApplicationService
    safari_route_application: SafariRouteApplicationService
    safari_capture_application: SafariCaptureApplicationService
    safari_finish_application: FinishSafariApplicationService
    start_safari_application: StartSafariApplicationService
    evolution_application: EvolutionApplicationService
    release_application: ReleaseApplicationService
    preview_release_application: PreviewReleaseApplicationService
    duplicate_application: DuplicateApplicationService
    profile_service: ProfileService
    creature_info_service: CreatureInfoService
    creature_collection_service: CreatureCollectionService
    species_info_service: SpeciesInfoService
    pokedex_service: PokedexService
    start_adventure_application: StartAdventureApplicationService
    energy_service: EnergyService
    trade_repository: NeonTradeRepository
    trade_application: TradeApplicationService
    trade_display_service: TradeDisplayService


def build_core(
    *,
    chance_calculator: CaptureChanceCalculator | None = None,
    ball_selector: CaptureBallSelector | None = None,
) -> CoreServices:
    """
    Builds the complete Core dependency graph.
    """

    species_repository = NeonSpeciesRepository()

    trainer_repository = NeonTrainerRepository()

    energy_repository = NeonEnergyRepository()

    energy_service = EnergyService(
        repository=energy_repository,
    )

    creature_repository = NeonCreatureRepository(
        species_repository=species_repository,
    )
    candy_repository = NeonCandyRepository()
    evolution_repository = NeonEvolutionRepository()
    reward_policy = RewardPolicy()

    creature_info_service = CreatureInfoService(
        creature_repository=creature_repository,
    )

    creature_collection_service = CreatureCollectionService(
        creature_repository=creature_repository,
        species_repository=species_repository,
    )

    species_info_service = SpeciesInfoService(
        species_repository=species_repository,
        creature_repository=creature_repository,
    )

    profile_repository = NeonProfileRepository()
    trade_repository = NeonTradeRepository()

    spawn_session_repository = InMemorySpawnSessionRepository()
    safari_activity_repository = InMemorySafariActivityRepository()
    safari_unlock_repository = NeonSafariUnlockRepository()

    stat_calculator = StatCalculator()

    chance_calculator = chance_calculator or CaptureChanceCalculator()

    ball_selector = ball_selector or CaptureBallSelector()

    capture_application = CaptureApplicationService(
        capture_service=CaptureService(
            chance_calculator=chance_calculator,
            ball_selector=ball_selector,
        ),
        unit_of_work=NeonCaptureUnitOfWork(),
        reward_policy=reward_policy,
        world_progress_service=SafariWorldProgressService(),
        spawn_session_repository=spawn_session_repository,
    )

    safari_random = random.Random()
    safari_registration_application = SafariRegistrationApplicationService(
        activity_repository=safari_activity_repository,
        unlock_repository=safari_unlock_repository,
    )
    safari_route_application = SafariRouteApplicationService(
        activity_repository=safari_activity_repository,
        route_option_factory=SafariRouteOptionFactory(),
        encounter_generator=SafariEncounterGenerator(
            species_repository=species_repository,
            opportunity_factory=OpportunityFactory(),
            random_source=safari_random,
        ),
        random_source=safari_random,
    )
    safari_capture_application = SafariCaptureApplicationService(
        activity_repository=safari_activity_repository,
        capture_resolver=SafariCaptureResolver(
            attempt_service=CaptureAttemptService(chance_calculator),
            random_source=safari_random,
        ),
        unit_of_work=NeonCaptureUnitOfWork(),
        reward_policy=reward_policy,
    )
    safari_finish_application = FinishSafariApplicationService(
        activity_repository=safari_activity_repository,
    )
    start_safari_application = StartSafariApplicationService(
        activity_repository=safari_activity_repository,
        unlock_repository=safari_unlock_repository,
        map_selector=SafariMapSelector(),
        weather_selector=SafariWeatherSelector(),
        time_of_day_selector=SafariTimeOfDaySelector(),
        encounter_generator=SafariEncounterGenerator(
            species_repository=species_repository,
            opportunity_factory=OpportunityFactory(),
            random_source=safari_random,
        ),
        random_source=safari_random,
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
    release_application = ReleaseApplicationService(
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        reward_policy=reward_policy,
    )

    preview_release_application = PreviewReleaseApplicationService(
        creature_repository=creature_repository,
        candy_repository=candy_repository,
        reward_policy=reward_policy,
    )
    duplicate_application = DuplicateApplicationService(
        creature_repository=creature_repository,
        species_repository=species_repository,
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
    start_adventure_application = StartAdventureApplicationService(
        species_repository=species_repository,
        creature_repository=creature_repository,
        trainer_repository=trainer_repository,
        energy_repository=energy_repository,
    )
    trade_application = TradeApplicationService(
        trade_repository=trade_repository,
        trainer_repository=trainer_repository,
        creature_repository=creature_repository,
    )
    trade_display_service = TradeDisplayService(
        trade_repository=trade_repository,
        creature_repository=creature_repository,
    )
    logger.info("Application services initialized")
    return CoreServices(
        species_repository=species_repository,
        creature_repository=creature_repository,
        trainer_repository=trainer_repository,
        candy_repository=candy_repository,
        spawn_session_repository=spawn_session_repository,
        stat_calculator=stat_calculator,
        spawn_application=spawn_application,
        select_opportunity_application=select_opportunity_application,
        get_current_spawn_application=get_current_spawn_application,
        capture_application=capture_application,
        safari_registration_application=safari_registration_application,
        safari_route_application=safari_route_application,
        safari_capture_application=safari_capture_application,
        safari_finish_application=safari_finish_application,
        start_safari_application=start_safari_application,
        evolution_application=evolution_application,
        release_application=release_application,
        preview_release_application=preview_release_application,
        duplicate_application=duplicate_application,
        profile_service=profile_service,
        creature_info_service=creature_info_service,
        creature_collection_service=creature_collection_service,
        species_info_service=species_info_service,
        pokedex_service=pokedex_service,
        start_adventure_application=start_adventure_application,
        energy_service=energy_service,
        trade_repository=trade_repository,
        trade_application=trade_application,
        trade_display_service=trade_display_service,
    )
