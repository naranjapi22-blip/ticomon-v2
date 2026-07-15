from __future__ import annotations

import json
import random
from uuid import uuid4

import pytest

from core.creature.base_stats import BaseStats
from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import Rarity
from core.safari.domain import SafariComposition, SafariThematicEvent, SafariZone
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.participant import SafariParticipant
from core.safari.route import SafariRouteOption
from core.species.species import Species
from core.species.species_metadata import SpeciesMetadata
from core.species.variant import Variant
from simulation.safari import (
    DEFAULT_PLAYER_STRATEGIES,
    CatalogSource,
    SafariPlayerStrategy,
    SafariSimulationConfig,
    SafariSimulationRunner,
)


def _species(
    *,
    species_id: int,
    name: str,
    rarity: Rarity = Rarity.COMMON,
    types: list[str] | None = None,
    pokeapi_id: int | None = None,
    baby: bool = False,
    legendary: bool = False,
    mythical: bool = False,
    variants: list[Variant] | None = None,
) -> Species:
    return Species(
        id=species_id,
        pokeapi_id=pokeapi_id if pokeapi_id is not None else species_id,
        name=name,
        types=types or ["normal"],
        base_stats=BaseStats(
            hp=45,
            attack=45,
            defense=45,
            special_attack=45,
            special_defense=45,
            speed=45,
        ),
        height=1,
        weight=1,
        capture_rate=45,
        spawn_rarity=rarity,
        metadata=SpeciesMetadata(
            generation=1,
            is_baby=baby,
            is_legendary=legendary,
            is_mythical=mythical,
        ),
        variants=variants or [],
    )


def _species_catalog() -> tuple[Species, ...]:
    ordinary_types = [
        ["normal"],
        ["water"],
        ["grass"],
        ["fire"],
        ["electric"],
        ["psychic"],
        ["rock"],
        ["ground"],
        ["flying"],
        ["dark"],
        ["steel"],
        ["bug"],
        ["poison"],
        ["ice"],
        ["dragon"],
        ["fairy"],
        ["fighting"],
        ["ghost"],
        ["water", "ice"],
        ["grass", "poison"],
        ["fire", "flying"],
        ["electric", "steel"],
        ["psychic", "fairy"],
        ["normal", "water"],
    ]
    rarity_cycle = [
        Rarity.VERY_COMMON,
        Rarity.COMMON,
        Rarity.UNCOMMON,
        Rarity.RARE,
        Rarity.VERY_RARE,
        Rarity.EPIC,
    ]
    ordinary = [
        _species(
            species_id=index,
            name=f"ordinary-{index}",
            rarity=rarity_cycle[(index - 1) % len(rarity_cycle)],
            types=ordinary_types[index - 1],
            baby=index in {7, 8, 9},
            variants=(
                [Variant(id=700 + index, name=f"Variant {index}")]
                if index in {7, 8, 9}
                else None
            ),
        )
        for index in range(1, len(ordinary_types) + 1)
    ]
    specials = (
        _species(
            species_id=101,
            name="regional-1",
            rarity=Rarity.RARE,
            pokeapi_id=10091,
            types=["steel"],
        ),
        _species(
            species_id=102,
            name="regional-2",
            rarity=Rarity.RARE,
            pokeapi_id=10092,
            types=["water"],
        ),
        _species(
            species_id=103,
            name="regional-3",
            rarity=Rarity.RARE,
            pokeapi_id=10100,
            types=["grass"],
        ),
        _species(
            species_id=104,
            name="legend",
            rarity=Rarity.LEGENDARY,
            types=["dragon"],
            legendary=True,
        ),
        _species(
            species_id=105,
            name="myth",
            rarity=Rarity.MYTHICAL,
            types=["fairy"],
            mythical=True,
        ),
    )
    return tuple(ordinary + list(specials))


def _common_encounter() -> SafariEncounter:
    opportunity_factory = OpportunityFactory()
    slots = tuple(
        SafariEncounterSlot(
            id=uuid4(),
            opportunity=opportunity_factory.create(_species_catalog()[index]),
        )
        for index in range(3)
    )
    return SafariEncounter(
        id=uuid4(),
        composition=SafariComposition.NORMAL,
        slots=slots,
    )


def _route_options() -> tuple[SafariRouteOption, ...]:
    return (
        SafariRouteOption(
            id="stay",
            source_zone=SafariZone.FOREST_ENTRANCE,
            destination_zone=SafariZone.FOREST_ENTRANCE,
            type_weight_modifiers={"normal": 1.0},
            allowed_events=(SafariThematicEvent.NONE,),
            narrative_key="stay",
        ),
        SafariRouteOption(
            id="advance",
            source_zone=SafariZone.FOREST_ENTRANCE,
            destination_zone=SafariZone.DEEP_FOREST,
            type_weight_modifiers={"normal": 1.0},
            allowed_events=(SafariThematicEvent.NONE,),
            narrative_key="advance",
        ),
    )


@pytest.mark.parametrize("strategy", DEFAULT_PLAYER_STRATEGIES)
def test_strategies_return_valid_slot_ball_and_route_choices(
    strategy: SafariPlayerStrategy,
):
    encounter = _common_encounter()
    participant = SafariParticipant(trainer_id=1, initial_balls=5, remaining_balls=5)
    rng = random.Random(7)

    slot = strategy.choose_slot(encounter, rng)
    balls = strategy.choose_balls(participant, slot, rng)
    route = strategy.choose_route_option(_route_options(), rng)

    assert slot in encounter.slots
    assert 1 <= balls <= 3
    assert balls <= participant.remaining_balls
    assert route in _route_options()


@pytest.mark.asyncio
async def test_same_seed_produces_same_report():
    config = SafariSimulationConfig(
        simulations=1,
        levels=(1,),
        participant_counts=(2,),
        strategy_names=("conservative",),
        seed=42,
        global_shiny_chance=0.0,
        species_source=CatalogSource.AUTO,
    )
    catalog = _species_catalog()
    first = await SafariSimulationRunner(config, species_catalog=catalog).run()
    second = await SafariSimulationRunner(config, species_catalog=catalog).run()

    assert first.to_dict() == second.to_dict()


@pytest.mark.asyncio
async def test_runner_reports_progress_during_runs():
    config = SafariSimulationConfig(
        simulations=3,
        levels=(1,),
        participant_counts=(2,),
        strategy_names=("conservative",),
        seed=42,
        global_shiny_chance=0.0,
        species_source=CatalogSource.AUTO,
    )
    progress_updates: list[tuple[int, int, str, int, int]] = []

    report = await SafariSimulationRunner(
        config,
        species_catalog=_species_catalog(),
    ).run(
        progress_callback=lambda *args: progress_updates.append(args),
    )

    assert report.scenarios[0].metrics.runs == 3
    assert progress_updates == [
        (1, 3, "conservative", 1, 2),
        (2, 3, "conservative", 1, 2),
        (3, 3, "conservative", 1, 2),
    ]


@pytest.mark.asyncio
async def test_different_seeds_can_change_the_report():
    base = SafariSimulationConfig(
        simulations=2,
        levels=(1,),
        participant_counts=(4,),
        strategy_names=("aggressive",),
        seed=42,
        global_shiny_chance=0.0,
        species_source=CatalogSource.AUTO,
    )
    catalog = _species_catalog()
    first = await SafariSimulationRunner(base, species_catalog=catalog).run()
    second = await SafariSimulationRunner(
        base.__class__(
            simulations=base.simulations,
            levels=base.levels,
            participant_counts=base.participant_counts,
            strategy_names=base.strategy_names,
            seed=99,
            global_shiny_chance=base.global_shiny_chance,
            species_source=base.species_source,
        ),
        species_catalog=catalog,
    ).run()

    assert first.to_dict() != second.to_dict()


@pytest.mark.asyncio
@pytest.mark.parametrize("participant_count", (2, 4, 6, 10))
async def test_runner_supports_requested_participant_counts(participant_count: int):
    config = SafariSimulationConfig(
        simulations=1,
        levels=(1,),
        participant_counts=(participant_count,),
        strategy_names=("random",),
        seed=17,
        global_shiny_chance=0.0,
        species_source=CatalogSource.AUTO,
    )
    report = await SafariSimulationRunner(
        config, species_catalog=_species_catalog()
    ).run()

    assert report.scenarios[0].participant_count == participant_count
    assert report.scenarios[0].metrics.runs == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("level", (1, 2, 3, 4, 5))
async def test_runner_supports_all_configured_levels(level: int):
    config = SafariSimulationConfig(
        simulations=1,
        levels=(level,),
        participant_counts=(2,),
        strategy_names=("fixed_1",),
        seed=5,
        global_shiny_chance=0.0,
        species_source=CatalogSource.AUTO,
    )
    report = await SafariSimulationRunner(
        config, species_catalog=_species_catalog()
    ).run()

    assert report.scenarios[0].level == level
    assert report.scenarios[0].metrics.runs == 1


@pytest.mark.asyncio
async def test_simulation_report_is_json_serializable_and_balanced():
    config = SafariSimulationConfig(
        simulations=1,
        levels=(1,),
        participant_counts=(2,),
        strategy_names=("conservative",),
        seed=7,
        global_shiny_chance=0.0,
        species_source=CatalogSource.AUTO,
    )
    report = await SafariSimulationRunner(
        config, species_catalog=_species_catalog()
    ).run()
    data = report.to_dict()

    json.dumps(data)
    scenario = data["scenarios"][0]
    assert scenario["balls"]["balanced"] is True
    assert (
        scenario["balls"]["initial"]
        == scenario["balls"]["spent"] + scenario["balls"]["remaining"]
    )
    assert scenario["balls"]["spent"] == scenario["balls"]["attempts_executed"]
    assert scenario["encounters"]["completed"] <= 5
    assert scenario["finalization"]["reasons"]


def test_balance_uses_spent_balls_not_committed_balls():
    from simulation.safari.metrics import ScenarioMetrics

    metrics = ScenarioMetrics(
        level=1,
        participant_count=2,
        strategy_name="random",
        catalog_species_count=0,
        catalog_regional_species_count=0,
    )
    metrics.balls_initial_total = 10
    metrics.balls_committed_total = 7
    metrics.attempts_executed_total = 4
    metrics.balls_not_executed_total = 3
    metrics.balls_remaining_total = 6

    balls = metrics.to_dict()["balls"]

    assert balls["spent"] == 4
    assert balls["committed_not_executed"] == 3
    assert balls["balanced"] is True


def test_balance_checks_report_anomalies_for_empty_metrics():
    from simulation.safari.metrics import ScenarioMetrics
    from simulation.safari.simulator import SafariSimulationRunner

    metrics = ScenarioMetrics(
        level=1,
        participant_count=2,
        strategy_name="random",
        catalog_species_count=0,
        catalog_regional_species_count=0,
    )
    SafariSimulationRunner._append_balance_checks(metrics)

    assert "no encounters were completed in the sample." in metrics.anomalies
