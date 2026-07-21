from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.creature.creature import Creature
from core.creature.creature_repository import CreatureRepository
from core.creature.stat import Stat
from core.species.species_repository import SpeciesRepository
from core.stats.stat_calculator import StatCalculator

POKEMON_TYPES = (
    "normal",
    "fire",
    "water",
    "electric",
    "grass",
    "ice",
    "fighting",
    "poison",
    "ground",
    "flying",
    "psychic",
    "bug",
    "rock",
    "ghost",
    "dragon",
    "dark",
    "steel",
    "fairy",
)


class TopMetric(str, Enum):
    OVERALL = "overall"
    PHYSICAL_ATTACK = "physical_attack"
    SPECIAL_ATTACK = "special_attack"
    PHYSICAL_DEFENSE = "physical_defense"
    SPECIAL_DEFENSE = "special_defense"
    SPEED = "speed"

    @property
    def label(self) -> str:
        return {
            TopMetric.OVERALL: "Total Stats",
            TopMetric.PHYSICAL_ATTACK: "Physical Attack",
            TopMetric.SPECIAL_ATTACK: "Special Attack",
            TopMetric.PHYSICAL_DEFENSE: "Physical Bulk",
            TopMetric.SPECIAL_DEFENSE: "Special Bulk",
            TopMetric.SPEED: "Speed",
        }[self]

    @property
    def selector_label(self) -> str:
        return {
            TopMetric.OVERALL: "Overall",
            TopMetric.PHYSICAL_ATTACK: "Physical Attack",
            TopMetric.SPECIAL_ATTACK: "Special Attack",
            TopMetric.PHYSICAL_DEFENSE: "Physical Defense",
            TopMetric.SPECIAL_DEFENSE: "Special Defense",
            TopMetric.SPEED: "Speed",
        }[self]


@dataclass(frozen=True)
class RankingDefinition:
    score_stats: tuple[str, ...]
    tie_break_stats: tuple[str, ...]
    uses_offensive_tie_break: bool = False


RANKING_DEFINITIONS = {
    TopMetric.OVERALL: RankingDefinition(
        score_stats=("Total Stats",),
        tie_break_stats=("Speed",),
    ),
    TopMetric.PHYSICAL_ATTACK: RankingDefinition(
        score_stats=("Attack",),
        tie_break_stats=("Total Stats", "Speed"),
    ),
    TopMetric.SPECIAL_ATTACK: RankingDefinition(
        score_stats=("Sp. Atk",),
        tie_break_stats=("Total Stats", "Speed"),
    ),
    TopMetric.PHYSICAL_DEFENSE: RankingDefinition(
        score_stats=("HP", "Defense"),
        tie_break_stats=("Defense", "HP", "Total Stats"),
    ),
    TopMetric.SPECIAL_DEFENSE: RankingDefinition(
        score_stats=("HP", "Sp. Def"),
        tie_break_stats=("Sp. Def", "HP", "Total Stats"),
    ),
    TopMetric.SPEED: RankingDefinition(
        score_stats=("Speed",),
        tie_break_stats=("Total Stats",),
        uses_offensive_tie_break=True,
    ),
}


@dataclass(frozen=True)
class RankedCreature:
    creature: Creature
    stats: dict[str, int]
    score: int
    metric: TopMetric


class CreatureCollectionService:
    def __init__(
        self,
        creature_repository: CreatureRepository,
        species_repository: SpeciesRepository,
        stat_calculator: StatCalculator | None = None,
    ) -> None:
        self._creature_repository = creature_repository
        self._species_repository = species_repository
        self._stat_calculator = stat_calculator or StatCalculator()

    async def get_top_rankings(
        self,
        trainer_id: int,
        *,
        metric: TopMetric = TopMetric.OVERALL,
        pokemon_type: str | None = None,
    ) -> list[RankedCreature]:
        metric = TopMetric(metric)
        creatures = await self._creature_repository.get_by_trainer(trainer_id)
        return self.rank_creatures(
            creatures,
            metric=metric,
            pokemon_type=pokemon_type,
        )

    def rank_snapshot(
        self,
        rankings: list[RankedCreature],
        *,
        metric: TopMetric,
        pokemon_type: str | None = None,
    ) -> list[RankedCreature]:
        """Re-rank an in-memory !top snapshot without database access."""
        return self.rank_creatures(
            [ranking.creature for ranking in rankings],
            metric=metric,
            pokemon_type=pokemon_type,
        )

    def rank_creatures(
        self,
        creatures: list[Creature],
        *,
        metric: TopMetric,
        pokemon_type: str | None = None,
    ) -> list[RankedCreature]:
        metric = TopMetric(metric)
        filtered_creatures = self._filter_ranked_types(creatures, pokemon_type)
        rankings = [
            self._ranked_creature(creature, metric) for creature in filtered_creatures
        ]
        return sorted(
            rankings,
            key=lambda item: self._ranking_sort_key(item),
        )

    def _ranked_creature(
        self,
        creature: Creature,
        metric: TopMetric,
    ) -> RankedCreature:
        stats = {
            "HP": self._stat_calculator.calculate(creature, Stat.HP),
            "Attack": self._stat_calculator.calculate(creature, Stat.ATTACK),
            "Defense": self._stat_calculator.calculate(creature, Stat.DEFENSE),
            "Sp. Atk": self._stat_calculator.calculate(creature, Stat.SP_ATTACK),
            "Sp. Def": self._stat_calculator.calculate(creature, Stat.SP_DEFENSE),
            "Speed": self._stat_calculator.calculate(creature, Stat.SPEED),
        }
        stats["Total Stats"] = sum(stats.values())
        definition = RANKING_DEFINITIONS[metric]
        score = sum(stats[key] for key in definition.score_stats)
        return RankedCreature(creature, stats, score, metric)

    def _ranking_sort_key(self, ranking: RankedCreature) -> tuple[int, ...]:
        definition = RANKING_DEFINITIONS[ranking.metric]
        stats = ranking.stats
        tie_breakers = [stats[key] for key in definition.tie_break_stats]
        if definition.uses_offensive_tie_break:
            tie_breakers.append(max(stats["Attack"], stats["Sp. Atk"]))

        collection_number = (
            ranking.creature.collection_number
            if ranking.creature.collection_number is not None
            else float("inf")
        )
        creature_id = (
            ranking.creature.id if ranking.creature.id is not None else float("inf")
        )
        return (
            -ranking.score,
            *(-value for value in tie_breakers),
            collection_number,
            creature_id,
        )

    def _filter_ranked_types(
        self,
        creatures: list[Creature],
        pokemon_type: str | None,
    ) -> list[Creature]:
        if pokemon_type is None:
            return creatures

        normalized_type = pokemon_type.strip().lower()
        if normalized_type not in POKEMON_TYPES:
            raise ValueError(f"Unknown Pokémon type: {pokemon_type}")

        return [
            creature
            for creature in creatures
            if normalized_type
            in {species_type.lower() for species_type in creature.species.types}
        ]

    async def get_top_collection(
        self,
        trainer_id: int,
        pokemon_type: str | None = None,
    ) -> list[Creature]:
        creatures = await self._creature_repository.get_by_trainer(trainer_id)

        creatures = await self._apply_type_filter(
            creatures,
            pokemon_type,
        )

        return sorted(
            creatures,
            key=lambda creature: (
                -creature.iv_percentage,
                (
                    -creature.collection_number
                    if creature.collection_number is not None
                    else 0
                ),
                -creature.id if creature.id is not None else 0,
            ),
        )

    async def get_recent_collection(
        self,
        trainer_id: int,
        pokemon_type: str | None = None,
        shiny_only: bool = False,
    ) -> list[Creature]:
        creatures = await self._creature_repository.get_by_trainer(trainer_id)

        if shiny_only:
            creatures = [creature for creature in creatures if creature.is_shiny]

        creatures = await self._apply_type_filter(
            creatures,
            pokemon_type,
        )

        return sorted(
            creatures,
            key=lambda creature: (
                -(
                    creature.collection_number
                    if creature.collection_number is not None
                    else 0
                ),
                creature.id if creature.id is not None else 0,
            ),
        )

    async def _apply_type_filter(
        self,
        creatures: list[Creature],
        pokemon_type: str | None,
    ) -> list[Creature]:
        if pokemon_type is None:
            return creatures

        normalized_type = pokemon_type.strip().lower()
        valid_types = await self._known_types()

        if normalized_type not in valid_types:
            raise ValueError(f"Unknown Pokémon type: {pokemon_type}")

        return [
            creature
            for creature in creatures
            if normalized_type
            in (species_type.lower() for species_type in creature.species.types)
        ]

    async def _known_types(self) -> set[str]:
        species = await self._species_repository.get_all()

        return {pokemon_type.lower() for item in species for pokemon_type in item.types}
