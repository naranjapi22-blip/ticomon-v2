from dataclasses import replace
from unittest.mock import patch

import pytest

from core.capture import CaptureAttemptResult, CaptureAttemptService
from core.capture.domain.capture_ball import CaptureBall
from core.capture.domain.capture_ball_catalog import CAPTURE_BALL_CONFIG
from core.capture.domain.capture_chance_calculator import CaptureChanceCalculator
from core.capture.domain.capture_result import CaptureResult
from core.capture.service import CaptureService
from core.opportunity.opportunity_factory import OpportunityFactory
from core.rarity import RARITY_CONFIG, Rarity
from core.safari.capture_config import SAFARI_BASE_CAPTURE
from test.factories import create_species


class FixedRandom:
    def __init__(self, roll: float) -> None:
        self.roll = roll
        self.calls = 0

    def random(self) -> float:
        self.calls += 1
        return self.roll


class FixedBallSelector:
    def __init__(self, ball: CaptureBall) -> None:
        self.ball = ball
        self.calls = 0

    def select(self) -> CaptureBall:
        self.calls += 1
        return self.ball


class RecordingChanceCalculator:
    def __init__(self, chance: float) -> None:
        self.chance = chance
        self.calls = []

    def calculate(self, opportunity, capture_ball) -> float:
        self.calls.append((opportunity, capture_ball))
        return self.chance


def make_opportunity(*, shiny: bool = False):
    opportunity = OpportunityFactory.create(create_species(id=25))
    opportunity.is_shiny = shiny
    return opportunity


@pytest.mark.parametrize(
    ("roll", "success", "failed_attempts"),
    [(0.49, True, 0), (0.50, False, 1)],
)
def test_pure_attempt_uses_explicit_ball_and_injected_random(
    roll,
    success,
    failed_attempts,
):
    opportunity = make_opportunity()
    calculator = RecordingChanceCalculator(0.50)
    random_source = FixedRandom(roll)
    service = CaptureAttemptService(calculator)  # type: ignore[arg-type]

    result = service.attempt(
        opportunity,
        CaptureBall.GREAT_BALL,
        random_source,  # type: ignore[arg-type]
    )

    assert isinstance(result, CaptureAttemptResult)
    assert result.success is success
    assert result.chance == 0.50
    assert result.roll == roll
    assert result.capture_ball == CaptureBall.GREAT_BALL
    assert result.opportunity.failed_attempts == failed_attempts
    assert calculator.calls == [(opportunity, CaptureBall.GREAT_BALL)]
    assert random_source.calls == 1


def test_pure_attempt_does_not_modify_original_opportunity():
    opportunity = make_opportunity(shiny=True)
    opportunity.failed_attempts = 2
    original_values = (
        opportunity.species,
        opportunity.ivs,
        opportunity.nature,
        opportunity.size,
        opportunity.is_shiny,
        opportunity.initial_form,
        opportunity.interaction,
    )
    service = CaptureAttemptService(RecordingChanceCalculator(0.25))  # type: ignore[arg-type]

    result = service.attempt(
        opportunity,
        CaptureBall.POKE_BALL,
        FixedRandom(0.90),  # type: ignore[arg-type]
    )

    assert opportunity.failed_attempts == 2
    assert result.opportunity is not opportunity
    assert result.opportunity.failed_attempts == 3
    assert (
        result.opportunity.species,
        result.opportunity.ivs,
        result.opportunity.nature,
        result.opportunity.size,
        result.opportunity.is_shiny,
        result.opportunity.initial_form,
        result.opportunity.interaction,
    ) == original_values
    assert not hasattr(result, "creature")


@pytest.mark.parametrize("capture_ball", tuple(CaptureBall))
def test_each_ball_uses_canonical_capture_configuration(capture_ball):
    opportunity = make_opportunity()
    calculator = CaptureChanceCalculator()
    service = CaptureAttemptService(calculator)
    expected_chance = calculator.calculate(opportunity, capture_ball)

    result = service.attempt(
        opportunity,
        capture_ball,
        FixedRandom(0.0),  # type: ignore[arg-type]
    )

    assert result.chance == expected_chance
    assert result.capture_ball == capture_ball
    assert capture_ball in CAPTURE_BALL_CONFIG


def test_great_ball_keeps_the_canonical_modifier_for_future_safari_use():
    assert CAPTURE_BALL_CONFIG[CaptureBall.GREAT_BALL].modifier == 1.20


def test_same_state_and_roll_are_deterministic():
    opportunity = make_opportunity()
    service = CaptureAttemptService(CaptureChanceCalculator())

    first = service.attempt(
        opportunity,
        CaptureBall.ULTRA_BALL,
        FixedRandom(0.20),  # type: ignore[arg-type]
    )
    second = service.attempt(
        opportunity,
        CaptureBall.ULTRA_BALL,
        FixedRandom(0.20),  # type: ignore[arg-type]
    )

    assert first == second


def test_shiny_does_not_change_capture_chance():
    regular = make_opportunity(shiny=False)
    shiny = make_opportunity(shiny=True)
    calculator = CaptureChanceCalculator()

    assert calculator.calculate(
        regular,
        CaptureBall.GREAT_BALL,
    ) == calculator.calculate(shiny, CaptureBall.GREAT_BALL)


@pytest.mark.parametrize("rarity", tuple(SAFARI_BASE_CAPTURE))
def test_safari_uses_base_capture_overrides_without_changing_spawn(
    rarity,
):
    opportunity = make_opportunity()
    opportunity.species = replace(opportunity.species, spawn_rarity=rarity)
    safari_calculator = CaptureChanceCalculator(
        base_capture_overrides=SAFARI_BASE_CAPTURE,
    )
    spawn_calculator = CaptureChanceCalculator()
    modifier = (opportunity.species.capture_rate / 255.0) ** 0.5
    ball_modifier = CAPTURE_BALL_CONFIG[CaptureBall.GREAT_BALL].modifier

    safari_chance = safari_calculator.calculate(
        opportunity,
        CaptureBall.GREAT_BALL,
    )
    spawn_chance = spawn_calculator.calculate(
        opportunity,
        CaptureBall.GREAT_BALL,
    )

    assert safari_chance == min(
        SAFARI_BASE_CAPTURE[rarity] * modifier * ball_modifier,
        RARITY_CONFIG[rarity].capture_cap,
    )
    assert spawn_chance == min(
        RARITY_CONFIG[rarity].base_capture * modifier * ball_modifier,
        RARITY_CONFIG[rarity].capture_cap,
    )


@pytest.mark.parametrize("rarity", (Rarity.LEGENDARY, Rarity.MYTHICAL))
def test_safari_keeps_ordinary_unique_rarity_parameters(rarity):
    opportunity = make_opportunity()
    opportunity.species = replace(opportunity.species, spawn_rarity=rarity)

    assert CaptureChanceCalculator(
        base_capture_overrides=SAFARI_BASE_CAPTURE,
    ).calculate(
        opportunity, CaptureBall.GREAT_BALL
    ) == CaptureChanceCalculator().calculate(
        opportunity,
        CaptureBall.GREAT_BALL,
    )


def test_safari_shiny_has_no_additional_capture_adjustment():
    regular = make_opportunity(shiny=False)
    shiny = make_opportunity(shiny=True)
    calculator = CaptureChanceCalculator(
        base_capture_overrides=SAFARI_BASE_CAPTURE,
    )

    assert calculator.calculate(
        regular,
        CaptureBall.GREAT_BALL,
    ) == calculator.calculate(shiny, CaptureBall.GREAT_BALL)


def test_capture_chance_still_respects_rarity_cap_and_fatigue():
    opportunity = make_opportunity()
    opportunity.failed_attempts = 10_000
    config = RARITY_CONFIG[opportunity.species.spawn_rarity]

    chance = CaptureChanceCalculator().calculate(
        opportunity,
        CaptureBall.ULTRA_BALL,
    )

    assert chance == config.capture_cap


def test_capture_service_still_selects_ball_and_creates_creature_on_success():
    opportunity = make_opportunity()
    selector = FixedBallSelector(CaptureBall.GREAT_BALL)
    random_source = FixedRandom(0.0)
    service = CaptureService(
        CaptureChanceCalculator(),
        selector,  # type: ignore[arg-type]
        random_source,  # type: ignore[arg-type]
    )

    result = service.capture(7, opportunity)

    assert isinstance(result, CaptureResult)
    assert result.success
    assert result.creature is not None
    assert result.creature.trainer_id == 7
    assert result.attempt.opportunity is opportunity
    assert result.attempt.capture_ball == CaptureBall.GREAT_BALL
    assert selector.calls == 1
    assert random_source.calls == 1


def test_capture_service_failure_preserves_public_fatigue_behavior():
    opportunity = make_opportunity()
    selector = FixedBallSelector(CaptureBall.POKE_BALL)
    service = CaptureService(
        RecordingChanceCalculator(0.10),  # type: ignore[arg-type]
        selector,  # type: ignore[arg-type]
        FixedRandom(0.90),  # type: ignore[arg-type]
    )

    with patch("core.capture.service.CreatureFactory.create") as create_creature:
        result = service.capture(7, opportunity)

    assert isinstance(result, CaptureResult)
    assert not result.success
    assert result.creature is None
    assert result.attempt.opportunity is opportunity
    assert opportunity.failed_attempts == 1
    create_creature.assert_not_called()


def test_capture_service_uses_the_attempt_service_chance_without_api_change():
    opportunity = make_opportunity()
    calculator = RecordingChanceCalculator(0.42)
    service = CaptureService(
        calculator,  # type: ignore[arg-type]
        FixedBallSelector(CaptureBall.ULTRA_BALL),  # type: ignore[arg-type]
        FixedRandom(0.99),  # type: ignore[arg-type]
    )

    result = service.capture(1, opportunity)

    assert result.attempt.chance == 0.42
    assert result.attempt.capture_ball == CaptureBall.ULTRA_BALL
    assert calculator.calls == [(opportunity, CaptureBall.ULTRA_BALL)]


def test_pure_attempt_never_calls_creature_factory():
    service = CaptureAttemptService(RecordingChanceCalculator(1.0))  # type: ignore[arg-type]

    with patch("core.creature.creature_factory.CreatureFactory.create") as create:
        result = service.attempt(
            make_opportunity(),
            CaptureBall.MASTER_BALL,
            FixedRandom(0.0),  # type: ignore[arg-type]
        )

    assert result.success
    create.assert_not_called()
