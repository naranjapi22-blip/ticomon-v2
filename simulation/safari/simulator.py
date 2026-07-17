from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence
from uuid import uuid4

from application.safari import (
    FinishSafariApplicationService,
    SafariCaptureApplicationService,
    SafariRegistrationApplicationService,
    SafariRouteApplicationService,
    StartSafariApplicationService,
)
from application.safari.activity_state import SafariActivityTracker
from core.candy.reward_policy import RewardPolicy
from core.capture.attempt_service import CaptureAttemptService
from core.capture.domain.capture_chance_calculator import CaptureChanceCalculator
from core.creature.base_stats import BaseStats
from core.creature.creature_factory import CreatureFactory
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari.capture_config import SAFARI_BASE_CAPTURE
from core.safari.capture_resolution import SafariCaptureResolver
from core.safari.domain import (
    SAFARI_LEVEL_CONFIGS,
    SafariSessionStatus,
)
from core.safari.encounter import SafariEncounter
from core.safari.map_selector import SafariMapSelector
from core.safari.route import SafariRouteOption
from core.safari.route_option_factory import SafariRouteOptionFactory
from core.safari.time_of_day_selector import SafariTimeOfDaySelector
from core.safari.unlock import SafariUnlock
from core.safari.weather_selector import SafariWeatherSelector
from core.spawn.spawn_rarity_classifier import SpawnRarityClassifier
from core.species.regional_species import is_regional_species
from core.species.species import Species
from core.species.species_metadata import SpeciesMetadata
from core.species.species_repository import SpeciesRepository
from infrastructure.safari.in_memory_safari_activity_repository import (
    InMemorySafariActivityRepository,
)
from simulation.safari.metrics import (
    SafariEncounterTrace,
    SafariRunTrace,
    ScenarioMetrics,
    build_encounter_trace,
    build_run_trace,
)
from simulation.safari.runtime import (
    CachedSpeciesRepository,
    CatalogSource,
    InMemoryCaptureUnitOfWork,
    InMemorySafariUnlockRepository,
    SafariSimulationRecorder,
    SimulationEncounterGenerator,
)
from simulation.safari.strategies import (
    DEFAULT_PLAYER_STRATEGIES,
    SafariPlayerStrategy,
)

SafariSimulationProgressCallback = Callable[[int, int, str, int, int], None]


@dataclass(frozen=True, slots=True)
class SafariSimulationConfig:
    simulations: int = 1_000
    levels: tuple[int, ...] = (1, 2, 3, 4, 5)
    participant_counts: tuple[int, ...] = (2, 4, 6, 10)
    strategy_names: tuple[str, ...] = tuple(
        strategy.name for strategy in DEFAULT_PLAYER_STRATEGIES
    )
    seed: int = 42
    global_shiny_chance: float = 0.001
    species_source: CatalogSource = CatalogSource.AUTO


@dataclass(frozen=True, slots=True)
class SafariScenarioReport:
    level: int
    participant_count: int
    strategy_name: str
    metrics: ScenarioMetrics

    def to_dict(self) -> dict:
        return self.metrics.to_dict()


@dataclass(frozen=True, slots=True)
class SafariSimulationReport:
    config: SafariSimulationConfig
    catalog_source: str
    catalog_size: int
    scenarios: tuple[SafariScenarioReport, ...]
    anomalies: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "config": {
                "simulations": self.config.simulations,
                "levels": list(self.config.levels),
                "participant_counts": list(self.config.participant_counts),
                "strategies": list(self.config.strategy_names),
                "seed": self.config.seed,
                "global_shiny_chance": self.config.global_shiny_chance,
                "species_source": self.config.species_source.value,
            },
            "catalog": {
                "source": self.catalog_source,
                "size": self.catalog_size,
            },
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "anomalies": list(self.anomalies),
        }


class SafariSimulationRunner:
    def __init__(
        self,
        config: SafariSimulationConfig,
        *,
        species_catalog: Sequence[Species] | None = None,
        species_repository: SpeciesRepository | None = None,
    ) -> None:
        self._config = config
        self._species_catalog = (
            tuple(species_catalog) if species_catalog is not None else None
        )
        self._species_repository = species_repository
        self._random = random.Random(config.seed)
        self._strategies_by_name = {
            strategy.name: strategy for strategy in DEFAULT_PLAYER_STRATEGIES
        }

    async def run(
        self,
        *,
        progress_callback: SafariSimulationProgressCallback | None = None,
    ) -> SafariSimulationReport:
        catalog, catalog_source = await self._load_species_catalog()
        scenarios: list[SafariScenarioReport] = []
        anomalies: list[str] = []

        strategy_names = self._config.strategy_names or tuple(self._strategies_by_name)
        for level in self._config.levels:
            for participant_count in self._config.participant_counts:
                for strategy_name in strategy_names:
                    strategy = self._require_strategy(strategy_name)
                    metrics = await self._run_scenario(
                        level=level,
                        participant_count=participant_count,
                        strategy=strategy,
                        catalog=catalog,
                        progress_callback=progress_callback,
                    )
                    scenarios.append(
                        SafariScenarioReport(
                            level=level,
                            participant_count=participant_count,
                            strategy_name=strategy_name,
                            metrics=metrics,
                        )
                    )
                    anomalies.extend(metrics.anomalies)

        return SafariSimulationReport(
            config=self._config,
            catalog_source=catalog_source,
            catalog_size=len(catalog),
            scenarios=tuple(scenarios),
            anomalies=tuple(anomalies),
        )

    async def _run_scenario(
        self,
        *,
        level: int,
        participant_count: int,
        strategy: SafariPlayerStrategy,
        catalog: Sequence[Species],
        progress_callback: SafariSimulationProgressCallback | None = None,
    ) -> ScenarioMetrics:
        metrics = ScenarioMetrics(
            level=level,
            participant_count=participant_count,
            strategy_name=strategy.name,
            catalog_species_count=len(catalog),
            catalog_regional_species_count=sum(
                1 for species in catalog if is_regional_species(species)
            ),
        )

        for run_index in range(self._config.simulations):
            run_seed = self._random.randrange(2**63)
            trace = await self._run_single_safari(
                level=level,
                participant_count=participant_count,
                strategy=strategy,
                catalog=catalog,
                run_seed=run_seed,
                run_index=run_index,
            )
            metrics.record_run(trace)
            if progress_callback is not None:
                progress_callback(
                    run_index + 1,
                    self._config.simulations,
                    strategy.name,
                    level,
                    participant_count,
                )

        self._append_balance_checks(metrics)
        return metrics

    async def _run_single_safari(
        self,
        *,
        level: int,
        participant_count: int,
        strategy: SafariPlayerStrategy,
        catalog: Sequence[Species],
        run_seed: int,
        run_index: int,
    ) -> SafariRunTrace:
        module_random_state = random.getstate()
        random.seed(run_seed)
        try:
            return await self._run_single_safari_with_seeded_module_random(
                level=level,
                participant_count=participant_count,
                strategy=strategy,
                catalog=catalog,
                run_seed=run_seed,
                run_index=run_index,
            )
        finally:
            random.setstate(module_random_state)

    async def _run_single_safari_with_seeded_module_random(
        self,
        *,
        level: int,
        participant_count: int,
        strategy: SafariPlayerStrategy,
        catalog: Sequence[Species],
        run_seed: int,
        run_index: int,
    ) -> SafariRunTrace:
        run_random = random.Random(run_seed)
        recorder = SafariSimulationRecorder(
            run_random,
            global_shiny_chance=self._config.global_shiny_chance,
        )
        species_repository = CachedSpeciesRepository(catalog)
        encounter_generator = SimulationEncounterGenerator(
            species_repository=species_repository,
            opportunity_factory=OpportunityFactory(),
            random_source=run_random,
            recorder=recorder,
        )

        activity_repository = InMemorySafariActivityRepository()
        activity_tracker = SafariActivityTracker()
        unlock_repository = InMemorySafariUnlockRepository()
        capture_unit_of_work = InMemoryCaptureUnitOfWork()
        reward_policy = RewardPolicy()
        capture_resolver = SafariCaptureResolver(
            attempt_service=CaptureAttemptService(
                CaptureChanceCalculator(
                    base_capture_overrides=SAFARI_BASE_CAPTURE,
                )
            ),
            random_source=run_random,
        )

        registration_service = SafariRegistrationApplicationService(
            activity_repository=activity_repository,
            unlock_repository=unlock_repository,
            activity_tracker=activity_tracker,
        )
        start_service = StartSafariApplicationService(
            activity_repository=activity_repository,
            unlock_repository=unlock_repository,
            map_selector=SafariMapSelector(),
            weather_selector=SafariWeatherSelector(),
            time_of_day_selector=SafariTimeOfDaySelector(),
            encounter_generator=encounter_generator,
            random_source=run_random,
            session_id_factory=uuid4,
        )
        capture_service = SafariCaptureApplicationService(
            activity_repository=activity_repository,
            capture_resolver=capture_resolver,
            unit_of_work=capture_unit_of_work,
            reward_policy=reward_policy,
            creature_factory=CreatureFactory,
            encounter_generator=encounter_generator,
            random_source=run_random,
        )
        route_service = SafariRouteApplicationService(
            activity_repository=activity_repository,
            route_option_factory=SafariRouteOptionFactory(),
            encounter_generator=encounter_generator,
            random_source=run_random,
        )
        finish_service = FinishSafariApplicationService(
            activity_repository=activity_repository,
            activity_tracker=activity_tracker,
            clock=lambda: datetime.now(timezone.utc),
        )

        guild_id = 10_000 + run_index + (level * 100) + participant_count
        unlock = SafariUnlock(
            id=run_index + 1,
            guild_id=guild_id,
            level=level,
            encounter_count=SAFARI_LEVEL_CONFIGS[level].encounter_count,
            balls_per_participant=SAFARI_LEVEL_CONFIGS[level].balls_per_participant,
            unlocked_at=datetime.now(timezone.utc),
        )
        await unlock_repository.save(unlock)

        await registration_service.open(
            guild_id=guild_id,
            trainer_id=1,
            opened_at=datetime.now(timezone.utc),
        )
        for trainer_id in range(2, participant_count + 1):
            await registration_service.join(guild_id=guild_id, trainer_id=trainer_id)

        await start_service.start_for_testing(
            guild_id=guild_id, started_at=datetime.now(timezone.utc)
        )

        encounter_traces: list[SafariEncounterTrace] = []
        composition_fallbacks = 0
        event_fallbacks = 0
        normal_fallbacks = 0

        while True:
            session = await activity_repository.get_session(guild_id)
            if session is None:
                break

            if session.status is SafariSessionStatus.ENCOUNTER:
                current_encounter = session.current_encounter
                if current_encounter is None:
                    raise RuntimeError("session expected an active encounter.")

                await self._apply_capture_selections(
                    capture_service=capture_service,
                    session=session,
                    encounter=current_encounter,
                    strategy=strategy,
                    random_source=run_random,
                    guild_id=guild_id,
                )
                await capture_service.close_capture_selection(guild_id)
                result = await capture_service.resolve_capture(guild_id)

                generation_record = recorder.consume_generation(current_encounter.id)
                encounter_traces.append(
                    build_encounter_trace(
                        encounter=current_encounter,
                        generated=generation_record.outcome.generated,
                        resolution=result.encounter_resolution,
                        global_shiny=generation_record.outcome.global_shiny_applied,
                    )
                )
                composition_fallbacks += generation_record.outcome.composition_fallbacks
                event_fallbacks += generation_record.outcome.event_fallbacks
                normal_fallbacks += generation_record.outcome.normal_fallbacks
                continue

            if session.status is SafariSessionStatus.ROUTE_DECISION:
                vote = await route_service.open_route_vote(
                    guild_id=guild_id,
                    opened_at=datetime.now(timezone.utc),
                )
                await self._apply_route_votes(
                    route_service=route_service,
                    guild_id=guild_id,
                    session=session,
                    options=vote.options,
                    strategy=strategy,
                    random_source=run_random,
                )
                await route_service.resolve_route_vote(guild_id)
                continue

            if session.status is SafariSessionStatus.FINISHED:
                break

            raise RuntimeError(f"unsupported Safari session status: {session.status}")

        finished = await finish_service.finish(guild_id)
        return build_run_trace(
            summary=finished.summary,
            encounter_traces=tuple(encounter_traces),
            composition_fallbacks=composition_fallbacks,
            event_fallbacks=event_fallbacks,
            normal_fallbacks=normal_fallbacks,
            anomalies=tuple(),
        )

    async def _apply_capture_selections(
        self,
        *,
        capture_service: SafariCaptureApplicationService,
        session,
        encounter: SafariEncounter,
        strategy: SafariPlayerStrategy,
        random_source: random.Random,
        guild_id: int,
    ) -> None:
        for trainer_id, participant in session.participants_by_trainer.items():
            if participant.remaining_balls <= 0:
                continue

            slot = strategy.choose_slot(encounter, random_source)
            balls = strategy.choose_balls(participant, slot, random_source)
            balls = min(balls, participant.remaining_balls)
            if balls <= 0:
                continue

            result = await capture_service.select_capture(
                guild_id=guild_id,
                trainer_id=trainer_id,
                slot_id=slot.id,
                ball_count=balls,
            )
            assert result.balls_selected == balls
            await capture_service.confirm_capture_selection(
                guild_id=guild_id,
                trainer_id=trainer_id,
            )

    async def _apply_route_votes(
        self,
        *,
        route_service: SafariRouteApplicationService,
        guild_id: int,
        session,
        options: tuple[SafariRouteOption, ...],
        strategy: SafariPlayerStrategy,
        random_source: random.Random,
    ) -> None:
        for trainer_id, participant in session.participants_by_trainer.items():
            option = strategy.choose_route_option(options, random_source)
            await route_service.cast_route_vote(
                guild_id=guild_id,
                trainer_id=trainer_id,
                option_id=option.id,
            )

    async def _load_species_catalog(self) -> tuple[Sequence[Species], str]:
        if self._species_catalog is not None:
            return self._species_catalog, "provided"
        if self._species_repository is not None:
            return tuple(await self._species_repository.get_all()), "repository"
        if self._config.species_source is CatalogSource.CSV:
            return _load_species_from_csv(Path("pokemon_data.csv")), "csv"
        if self._config.species_source is CatalogSource.NEON:
            from infrastructure.species.neon_species_repository import (
                NeonSpeciesRepository,
            )

            species = await NeonSpeciesRepository().get_all()
            return species, "neon"

        try:
            from infrastructure.species.neon_species_repository import (
                NeonSpeciesRepository,
            )

            species = await NeonSpeciesRepository().get_all()
            return species, "neon"
        except Exception:
            return _load_species_from_csv(Path("pokemon_data.csv")), "csv"

    def _require_strategy(self, strategy_name: str) -> SafariPlayerStrategy:
        strategy = self._strategies_by_name.get(strategy_name)
        if strategy is None:
            raise ValueError(f"unknown Safari simulation strategy: {strategy_name}")
        return strategy

    @staticmethod
    def _append_balance_checks(metrics: ScenarioMetrics) -> None:
        if metrics.map_counts and not metrics.time_counts:
            metrics.anomalies.append("time of day was never selected.")
        if metrics.encounters_completed_total == 0:
            metrics.anomalies.append("no encounters were completed in the sample.")


def _load_species_from_csv(csv_path: Path) -> tuple[Species, ...]:
    classifier = SpawnRarityClassifier()
    species: list[Species] = []
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            hp = int(row["hp"])
            attack = int(row["attack"])
            defense = int(row["defense"])
            special_attack = int(row["special_attack"])
            special_defense = int(row["special_defense"])
            speed = int(row["speed"])
            stats = BaseStats(
                hp=hp,
                attack=attack,
                defense=defense,
                special_attack=special_attack,
                special_defense=special_defense,
                speed=speed,
            )
            base_stat_total = sum(
                (
                    hp,
                    attack,
                    defense,
                    special_attack,
                    special_defense,
                    speed,
                )
            )
            rarity = classifier.classify(
                capture_rate=int(row["capture_rate"]),
                base_stat_total=base_stat_total,
                is_legendary=row["is_legendary"].lower() == "true",
                is_mythical=row["is_mythical"].lower() == "true",
                stage=1,
            )
            species.append(
                Species(
                    id=int(row["id"]),
                    pokeapi_id=int(row["pokeapi_id"]),
                    name=row["name"],
                    types=[
                        part.strip() for part in row["types"].split(",") if part.strip()
                    ],
                    base_stats=stats,
                    height=int(row["height"]),
                    weight=int(row["weight"]),
                    capture_rate=int(row["capture_rate"]),
                    spawn_rarity=rarity,
                    metadata=SpeciesMetadata(
                        generation=1,
                        is_baby=False,
                        is_legendary=row["is_legendary"].lower() == "true",
                        is_mythical=row["is_mythical"].lower() == "true",
                    ),
                )
            )
    return tuple(species)
