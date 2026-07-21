from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord

from application.creature.creature_collection_service import (
    POKEMON_TYPES,
    RankedCreature,
    TopMetric,
)
from interfaces.discord.views.creature_list_view import CreatureListView

METRIC_LABELS = {metric: metric.label for metric in TopMetric}
STAT_LABELS = (
    ("HP", "HP"),
    ("Attack", "Atk"),
    ("Defense", "Def"),
    ("Sp. Atk", "SpA"),
    ("Sp. Def", "SpD"),
    ("Speed", "Spe"),
)


def format_ranked_creature_entry(
    ranking: RankedCreature,
    position: int,
) -> str:
    creature = ranking.creature
    stats = ranking.stats
    shiny = "✨ " if creature.is_shiny else ""
    name = creature.species.name.title()
    current_form = getattr(creature, "current_form", None)
    if current_form is not None:
        name = f"{name} ({current_form.name.title()})"
    types = " / ".join(
        type_name.title() for type_name in getattr(creature.species, "types", ())
    )
    total_stats = stats.get(
        "Total Stats",
        sum(stats[key] for key, _ in STAT_LABELS),
    )
    stat_line = " · ".join(f"{label} {stats[key]}" for key, label in STAT_LABELS)
    return (
        f"#{position} · {shiny}{name} · Collection #{creature.collection_number}\n"
        f"{ranking.metric.label}: {ranking.score} · Total Stats: "
        f"{total_stats}\n"
        f"{stat_line}\n"
        f"{types} · IVs: {creature.iv_percentage}%"
    )


class _MetricSelect(discord.ui.Select):
    def __init__(self, view: "TopCreatureView") -> None:
        super().__init__(
            placeholder="Sort by ranking",
            options=[
                discord.SelectOption(label=metric.selector_label, value=metric.value)
                for metric in TopMetric
            ],
            row=0,
        )
        self.top_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.top_view.update_filters(
            interaction,
            metric=TopMetric(self.values[0]),
            pokemon_type=self.top_view.pokemon_type,
        )


class _TypeSelect(discord.ui.Select):
    def __init__(self, view: "TopCreatureView") -> None:
        super().__init__(
            placeholder="Filter by type",
            options=[
                discord.SelectOption(label="All Types", value="all"),
                *(
                    discord.SelectOption(
                        label=type_name.title(),
                        value=type_name,
                    )
                    for type_name in POKEMON_TYPES
                ),
            ],
            row=1,
        )
        self.top_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        value = self.values[0]
        await self.top_view.update_filters(
            interaction,
            metric=self.top_view.metric,
            pokemon_type=None if value == "all" else value,
        )


class TopCreatureView(CreatureListView):
    def __init__(
        self,
        *,
        author_id: int,
        trainer_id: int,
        rankings: list[RankedCreature],
        metric: TopMetric,
        pokemon_type: str | None,
        load_rankings: Callable[
            [TopMetric, str | None], Awaitable[list[RankedCreature]]
        ],
    ) -> None:
        self.trainer_id = trainer_id
        self.metric = metric
        self.pokemon_type = pokemon_type
        self.rankings = rankings
        self._load_rankings = load_rankings
        super().__init__(
            author_id=author_id,
            title=self._title(),
            entries=self._format_entries(rankings),
        )
        self.remove_item(self.previous_button)
        self.remove_item(self.next_button)
        self.previous_button.row = 2
        self.next_button.row = 2
        self.add_item(self.previous_button)
        self.add_item(self.next_button)
        self.metric_select = _MetricSelect(self)
        self.type_select = _TypeSelect(self)
        self.add_item(self.metric_select)
        self.add_item(self.type_select)

    def _format_entries(self, rankings: list[RankedCreature]) -> list[str]:
        return [
            format_ranked_creature_entry(ranking, position)
            for position, ranking in enumerate(rankings, start=1)
        ]

    def _title(self) -> str:
        title = f"Top {self.metric.label} Pokémon"
        if self.pokemon_type is not None:
            title = f"{title} · Type: {self.pokemon_type.title()}"
        return title

    def build_embed(self) -> discord.Embed:
        embed = super().build_embed()
        embed.set_footer(
            text=(
                f"Page {self.page + 1}/{self.total_pages} · "
                f"{len(self.rankings)} creatures · Level 50 · 0 EVs"
            )
        )
        if not self.rankings:
            embed.description = "No creatures match the selected type."
        return embed

    async def update_filters(
        self,
        interaction: discord.Interaction,
        *,
        metric: TopMetric | None = None,
        pokemon_type: str | None = None,
    ) -> None:
        if metric is not None:
            self.metric = metric
        self.pokemon_type = pokemon_type
        self.rankings = await self._load_rankings(self.metric, self.pokemon_type)
        self.entries = self._format_entries(self.rankings)
        self.title = self._title()
        self.page = 0
        self.total_pages = max(
            1,
            (len(self.entries) + self.PAGE_SIZE - 1) // self.PAGE_SIZE,
        )
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)
