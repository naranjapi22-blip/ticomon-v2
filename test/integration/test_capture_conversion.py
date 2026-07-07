from unittest.mock import patch

import pytest

from core.capture.domain.capture_ball_selector import CaptureBallSelector
from core.capture.domain.capture_chance_calculator import (
    CaptureChanceCalculator,
)
from core.capture.service import CaptureService
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.spawn_factory import SpawnFactory
from core.spawn.world import World
from infrastructure.species.neon_species_repository import NeonSpeciesRepository


@pytest.mark.asyncio
@patch(
    "core.capture.service.random.random",
    return_value=0.0,
)
async def test_capture_converts_opportunity_into_creature(
    mock_random,
):
    repository = NeonSpeciesRepository()

    spawn_service = SpawnFactory.create(repository)

    context = SpawnContext(
        world=World.MAIN,
        region=Region.KANTO,
        event=None,
    )

    profile = SpawnProfile(
        opportunity_count=1,
    )

    opportunities = await spawn_service.spawn(
        context=context,
        profile=profile,
    )

    opportunity = opportunities[0]

    capture_service = CaptureService(
        chance_calculator=CaptureChanceCalculator(),
        ball_selector=CaptureBallSelector(),
    )

    result = capture_service.capture(
        opportunity=opportunity,
        trainer_id=1,
    )

    assert result.success is True

    creature = result.creature

    assert creature is not None
    assert creature.species == opportunity.species
    assert creature.ivs == opportunity.ivs
    assert creature.nature == opportunity.nature
    assert creature.size == opportunity.size
    assert creature.is_shiny == opportunity.is_shiny
