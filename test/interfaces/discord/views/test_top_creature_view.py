from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.creature.creature_collection_service import RankedCreature, TopMetric
from interfaces.discord.views.top_creature_view import TopCreatureView


def _ranking(collection_number: int, metric: TopMetric = TopMetric.OVERALL):
    creature = SimpleNamespace(
        collection_number=collection_number,
        species=SimpleNamespace(name="Pikachu", types=["electric"]),
        is_shiny=False,
        iv_percentage=100,
    )
    stats = {
        "HP": 100,
        "Attack": 100,
        "Defense": 100,
        "Sp. Atk": 100,
        "Sp. Def": 100,
        "Speed": 100,
    }
    return RankedCreature(creature, stats, sum(stats.values()), metric)


def _interaction():
    return SimpleNamespace(
        user=SimpleNamespace(id=1),
        response=SimpleNamespace(edit_message=AsyncMock()),
    )


@pytest.mark.asyncio
async def test_top_view_updates_metric_and_type_in_same_message():
    load_rankings = AsyncMock(return_value=[_ranking(2, TopMetric.SPEED)])
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=[_ranking(1)],
        metric=TopMetric.OVERALL,
        pokemon_type=None,
        load_rankings=load_rankings,
    )
    interaction = _interaction()

    await view.update_filters(
        interaction,
        metric=TopMetric.SPEED,
        pokemon_type="electric",
    )

    load_rankings.assert_awaited_once_with(TopMetric.SPEED, "electric")
    interaction.response.edit_message.assert_awaited_once()
    assert view.page == 0
    assert "Speed" in view.title
    assert "Electric" in view.title


def test_top_view_exposes_all_metrics_and_pokemon_types() -> None:
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=[_ranking(1)],
        metric=TopMetric.OVERALL,
        pokemon_type=None,
        load_rankings=AsyncMock(return_value=[]),
    )

    metric_select, type_select = view.children[2:]
    assert len(metric_select.options) == 6
    assert len(type_select.options) == 19
    assert type_select.options[0].label == "All Types"
    assert view.title == "Ranking: Total Stats · Type: All Types"
    assert view.build_embed().footer.text == "Page 1/1 · 1 creatures · Level 50 · 0 EVs"


def test_top_view_paginates_large_snapshots() -> None:
    rankings = [_ranking(index) for index in range(1, 102)]
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=rankings,
        metric=TopMetric.OVERALL,
        pokemon_type=None,
        load_rankings=AsyncMock(return_value=[]),
    )

    embed = view.build_embed()
    assert view.total_pages == 11
    assert embed.footer.text == "Page 1/11 · 101 creatures · Level 50 · 0 EVs"
    assert len(embed.description) <= 4096


@pytest.mark.asyncio
async def test_top_view_shows_empty_type_result_and_resets_page() -> None:
    load_rankings = AsyncMock(return_value=[])
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=[_ranking(index) for index in range(1, 12)],
        metric=TopMetric.OVERALL,
        pokemon_type=None,
        load_rankings=load_rankings,
    )
    view.page = 1
    interaction = _interaction()

    await view.update_filters(interaction, pokemon_type="fairy")

    assert view.page == 0
    assert view.build_embed().description == "No creatures match the selected type."


@pytest.mark.asyncio
async def test_top_view_rejects_other_users() -> None:
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=[_ranking(1)],
        metric=TopMetric.OVERALL,
        pokemon_type=None,
        load_rankings=AsyncMock(return_value=[]),
    )
    response = SimpleNamespace(send_message=AsyncMock())
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=2),
        response=response,
    )

    assert await view.interaction_check(interaction) is False
    response.send_message.assert_awaited_once()
    assert response.send_message.await_args.kwargs["ephemeral"] is True


@pytest.mark.asyncio
async def test_top_view_timeout_disables_all_controls() -> None:
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=[_ranking(1)],
        metric=TopMetric.OVERALL,
        pokemon_type=None,
        load_rankings=AsyncMock(return_value=[]),
    )

    await view.on_timeout()

    assert all(item.disabled for item in view.children)


def test_top_entry_is_one_line_and_contains_only_ranking_summary() -> None:
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=[_ranking(76)],
        metric=TopMetric.OVERALL,
        pokemon_type=None,
        load_rankings=AsyncMock(return_value=[]),
    )

    entry = view.entries[0]

    assert entry.count("\n") == 0
    assert entry.startswith("#1")
    assert "· #76 ·" in entry
    assert "Collection #" not in entry
    assert "Total Stats: 600" in entry
    assert "IVs: 100%" in entry
    assert "HP 100" not in entry
    assert "Electric" not in entry
    assert entry.count("Total Stats") == 1


@pytest.mark.parametrize(
    ("metric", "label", "score"),
    [
        (TopMetric.PHYSICAL_ATTACK, "Physical Attack", 100),
        (TopMetric.SPECIAL_ATTACK, "Special Attack", 100),
        (TopMetric.PHYSICAL_DEFENSE, "Physical Bulk", 200),
        (TopMetric.SPECIAL_DEFENSE, "Special Bulk", 200),
        (TopMetric.SPEED, "Speed", 100),
    ],
)
def test_top_entry_uses_active_metric_label(
    metric: TopMetric,
    label: str,
    score: int,
) -> None:
    ranking = _ranking(1, metric)
    ranking = RankedCreature(ranking.creature, ranking.stats, score, metric)
    view = TopCreatureView(
        author_id=1,
        trainer_id=1,
        rankings=[ranking],
        metric=metric,
        pokemon_type=None,
        load_rankings=AsyncMock(return_value=[]),
    )

    assert f"{label}: {score}" in view.entries[0]
    assert "\n" not in view.entries[0]
