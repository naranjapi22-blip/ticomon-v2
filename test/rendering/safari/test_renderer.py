from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application.safari import (
    SafariFinalSummary,
    SafariParticipantSummary,
    SafariRouteSegmentSummary,
    SafariRouteSummary,
    SafariTotalsSummary,
)
from core.opportunity.opportunity_factory import OpportunityFactory
from core.safari import (
    SafariMap,
    SafariPhase,
    SafariTimeOfDay,
    SafariWeather,
    SafariZone,
)
from core.safari.domain import SafariFinishReason
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.participant import SafariParticipant
from rendering.safari.renderer import SafariEncounterRenderer, SafariSummaryRenderer
from test.factories import create_species


def _session(slot_count: int = 3):
    participant = SafariParticipant(1, 3, 3)
    encounter = SafariEncounter(
        id=__import__("uuid").uuid4(),
        composition=SimpleNamespace(value="NORMAL"),
        slots=tuple(
            SafariEncounterSlot(
                uuid4(),
                OpportunityFactory.create(create_species(id=25 + index)),
            )
            for index in range(slot_count)
        ),
    )
    session = SimpleNamespace(
        current_encounter=encounter,
        safari_map=SafariMap.FOREST,
        weather=SafariWeather.CLEAR,
        time_of_day=SafariTimeOfDay.DAY,
        phase=SafariPhase.START,
        completed_encounter_count=0,
        total_encounters=5,
        current_segment=SimpleNamespace(remaining_encounters=3),
        participants_by_trainer={1: participant},
    )
    return session


def _summary() -> SafariFinalSummary:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    captured = SimpleNamespace(
        collection_number=7,
        species=create_species(id=25),
        is_shiny=True,
        current_form=None,
    )
    ranking = (
        SafariParticipantSummary(
            rank=1,
            trainer_id=1,
            capture_count=1,
            shiny_capture_count=1,
            captured_creatures=(captured,),
            initial_balls=3,
            balls_used=2,
            balls_remaining=1,
            attempts_executed=2,
            slots_won=1,
            encounters_participated=1,
        ),
    )
    route = SafariRouteSummary(
        safari_map=SafariMap.FOREST,
        weather=SafariWeather.CLEAR,
        time_of_day=SafariTimeOfDay.DAY,
        segments=(
            SafariRouteSegmentSummary(
                zone=SafariZone.FOREST_ENTRANCE,
                phase=SafariPhase.START,
                remaining_encounters=3,
                source_option_id=None,
            ),
        ),
    )
    encounters = (
        SimpleNamespace(
            slot_summaries=(
                SimpleNamespace(
                    slot_id=uuid4(),
                    species=create_species(id=25),
                    captured_creature=SimpleNamespace(
                        collection_number=7,
                        trainer_id=1,
                    ),
                ),
            )
        ),
    )
    return SafariFinalSummary(
        guild_id=10,
        session_id=uuid4(),
        level=4,
        safari_map=SafariMap.FOREST,
        weather=SafariWeather.CLEAR,
        time_of_day=SafariTimeOfDay.DAY,
        started_at=now,
        finished_at=now,
        finish_reason=SafariFinishReason.COMPLETED,
        ranking=ranking,
        route=route,
        encounters=encounters,
        totals=SafariTotalsSummary(
            encounters_completed=1,
            pokemon_seen=3,
            slots_captured=1,
            slots_escaped=2,
            attempts_executed=2,
            balls_committed=2,
        ),
        extraordinary=SimpleNamespace(
            legendary_seen=False,
            mythical_seen=False,
            shiny_encounter_seen=True,
            regional_herd_seen=False,
        ),
    )


@pytest.mark.parametrize("slot_count", [1, 2, 3, 5])
def test_encounter_renderer_renders_supported_slot_counts(slot_count: int) -> None:
    image = SafariEncounterRenderer().render(_session(slot_count))

    assert image.size == (1020, 574)
    assert image.getbbox() is not None


def test_encounter_renderer_formats_long_species_names() -> None:
    assert (
        SafariEncounterRenderer.format_species_name("Dudunsparce-Two-Segment")
        == "Dudunsparce (Two-Segment)"
    )


def test_summary_renderer_renders_final_banner() -> None:
    image = SafariSummaryRenderer().render(_summary())

    assert image.size == (1020, 574)
    assert image.getbbox() is not None
