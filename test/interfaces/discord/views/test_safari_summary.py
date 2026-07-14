from types import SimpleNamespace

from core.safari.domain import SafariFinishReason
from interfaces.discord.views.safari_summary import SafariSummaryView


def _summary(
    finish_reason: SafariFinishReason,
    *,
    ranking: tuple[SimpleNamespace, ...],
    extraordinary: SimpleNamespace,
) -> SimpleNamespace:
    return SimpleNamespace(
        safari_map=SimpleNamespace(value="FOREST"),
        weather=SimpleNamespace(value="CLEAR"),
        time_of_day=SimpleNamespace(value="DAY"),
        finish_reason=finish_reason,
        level=4,
        encounters_completed=2,
        ranking=ranking,
        totals=SimpleNamespace(encounters_completed=2),
        extraordinary=extraordinary,
    )


def test_summary_view_shows_only_top_three_and_no_final_image() -> None:
    summary = _summary(
        SafariFinishReason.COMPLETED,
        ranking=(
            SimpleNamespace(rank=1, trainer_id=101, capture_count=3),
            SimpleNamespace(rank=2, trainer_id=102, capture_count=2),
            SimpleNamespace(rank=3, trainer_id=103, capture_count=1),
            SimpleNamespace(rank=4, trainer_id=104, capture_count=0),
        ),
        extraordinary=SimpleNamespace(
            legendary_seen=True,
            mythical_seen=False,
            shiny_encounter_seen=True,
            regional_herd_seen=False,
        ),
    )

    view = SafariSummaryView(SimpleNamespace(summary=summary))
    embeds = view.build_embeds()

    assert len(embeds) == 1
    assert embeds[0].title == "Safari Complete"
    assert "Top Captures" in embeds[0].description
    assert "1. <@101> — 3" in embeds[0].description
    assert "2. <@102> — 2" in embeds[0].description
    assert "3. <@103> — 1" in embeds[0].description
    assert "<@104>" not in embeds[0].description


def test_summary_view_shows_zero_captures_message() -> None:
    summary = _summary(
        SafariFinishReason.COMPLETED,
        ranking=(),
        extraordinary=SimpleNamespace(
            legendary_seen=False,
            mythical_seen=False,
            shiny_encounter_seen=False,
            regional_herd_seen=False,
        ),
    )

    view = SafariSummaryView(SimpleNamespace(summary=summary))
    embeds = view.build_embeds()

    assert len(embeds) == 1
    assert embeds[0].description == "No Pokémon were captured during this expedition."


def test_summary_view_does_not_show_false_special_encounters() -> None:
    summary = _summary(
        SafariFinishReason.COMPLETED,
        ranking=(),
        extraordinary=SimpleNamespace(
            legendary_seen=False,
            mythical_seen=False,
            shiny_encounter_seen=False,
            regional_herd_seen=False,
        ),
    )

    view = SafariSummaryView(SimpleNamespace(summary=summary))

    assert len(view.build_embeds()) == 1
