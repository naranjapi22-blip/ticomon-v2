from types import SimpleNamespace

from interfaces.discord.views.safari_summary import SafariSummaryView


def test_summary_view_builds_embeds_from_session_summary() -> None:
    summary = SimpleNamespace(
        safari_map=SimpleNamespace(value="FOREST"),
        weather=SimpleNamespace(value="CLEAR"),
        time_of_day=SimpleNamespace(value="DAY"),
        finish_reason=SimpleNamespace(value="completed"),
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

    assert len(embeds) == 4
    assert embeds[0].title == "Safari Summary"
    assert embeds[1].title == "Safari Ranking"
    assert embeds[2].title == "Safari Route"
    assert embeds[3].title == "Safari Encounters"
