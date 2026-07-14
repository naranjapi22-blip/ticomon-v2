from types import SimpleNamespace

import pytest

from core.safari.domain import SafariFinishReason
from interfaces.discord.views.safari_summary import SafariSummaryView


@pytest.mark.parametrize(
    ("finish_reason", "expected_text"),
    [
        (
            SafariFinishReason.COMPLETED,
            "The expedition was completed successfully.",
        ),
        (
            SafariFinishReason.NO_BALLS_REMAINING,
            "The expedition ended because no Safari Balls remained.",
        ),
        (
            SafariFinishReason.ADMINISTRATIVE_ABORT,
            "The expedition was ended by an administrator.",
        ),
    ],
)
def test_summary_view_builds_embeds_from_session_summary(
    finish_reason: SafariFinishReason,
    expected_text: str,
) -> None:
    summary = SimpleNamespace(
        safari_map=SimpleNamespace(value="FOREST"),
        weather=SimpleNamespace(value="CLEAR"),
        time_of_day=SimpleNamespace(value="DAY"),
        finish_reason=finish_reason,
        level=4,
        totals=SimpleNamespace(
            encounters_completed=2,
            pokemon_seen=5,
            slots_captured=3,
            slots_escaped=2,
            attempts_executed=4,
            balls_committed=6,
        ),
        extraordinary=SimpleNamespace(
            legendary_seen=True,
            mythical_seen=False,
            shiny_encounter_seen=True,
            regional_herd_seen=False,
        ),
        ranking=(
            SimpleNamespace(
                rank=1,
                trainer_id=101,
                capture_count=2,
                shiny_capture_count=1,
                balls_used=3,
                balls_remaining=1,
                attempts_executed=4,
                slots_won=2,
                encounters_participated=2,
                captured_creatures=(
                    SimpleNamespace(
                        collection_number=7,
                        species=SimpleNamespace(name="pikachu"),
                        is_shiny=True,
                        current_form=None,
                    ),
                ),
            ),
        ),
        route=SimpleNamespace(
            safari_map=SimpleNamespace(value="FOREST"),
            weather=SimpleNamespace(value="CLEAR"),
            time_of_day=SimpleNamespace(value="DAY"),
            segments=(
                SimpleNamespace(
                    zone=SimpleNamespace(value="FOREST_ENTRANCE"),
                    phase=SimpleNamespace(value="START"),
                    remaining_encounters=2,
                    source_option_id=None,
                    vote_result=None,
                ),
            ),
        ),
        encounters=(
            SimpleNamespace(
                slot_summaries=(
                    SimpleNamespace(
                        slot_id="slot-1",
                        species=SimpleNamespace(name="pikachu"),
                        captured_creature=SimpleNamespace(
                            collection_number=7,
                            trainer_id=101,
                        ),
                    ),
                )
            ),
        ),
    )

    view = SafariSummaryView(SimpleNamespace(summary=summary))
    embeds = view.build_embeds()

    assert len(embeds) == 3
    assert embeds[0].title == "Safari Complete"
    assert embeds[1].title == "Ranking"
    assert embeds[2].title == "Special Encounters"
    assert expected_text in embeds[0].description
    assert "The expedition ended after 2 encounters." in embeds[0].description
    assert "Safari Encounters" not in embeds[0].description
    assert "Safari Route" not in embeds[0].description
    assert "UUID" not in embeds[0].description
    assert "No" not in embeds[2].description
    assert "collection_number" not in embeds[0].description
    assert "balls used" not in embeds[0].description.lower()


def test_summary_view_omits_special_encounters_when_none_occurred() -> None:
    summary = SimpleNamespace(
        safari_map=SimpleNamespace(value="FOREST"),
        weather=SimpleNamespace(value="CLEAR"),
        time_of_day=SimpleNamespace(value="DAY"),
        finish_reason=SafariFinishReason.COMPLETED,
        level=4,
        totals=SimpleNamespace(encounters_completed=1),
        extraordinary=SimpleNamespace(
            legendary_seen=False,
            mythical_seen=False,
            shiny_encounter_seen=False,
            regional_herd_seen=False,
        ),
        ranking=(),
    )

    view = SafariSummaryView(SimpleNamespace(summary=summary))

    assert len(view.build_embeds()) == 2
