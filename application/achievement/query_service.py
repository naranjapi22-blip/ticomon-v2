from dataclasses import dataclass

from core.achievement.definition import ACHIEVEMENT_DEFINITIONS, AchievementCriterion
from core.candy.candy_bundle import CandyBundle

ACHIEVEMENT_PRESENTATION = {
    "first_capture": ("First Capture", "Capture your first creature."),
    "captures_10": ("Ten Captures", "Capture 10 creatures."),
    "captures_50": ("Fifty Captures", "Capture 50 creatures."),
    "first_shiny_capture": ("First Shiny", "Capture a shiny creature."),
    "unique_species_10": ("Explorer", "Discover 10 unique species."),
    "first_completed_trade": ("First Trade", "Complete a trade."),
    "first_safari_capture": ("Safari Catch", "Capture a creature in Safari."),
}
ACHIEVEMENT_PRESENTATION.update(
    {
        definition.id.value: (
            definition.id.value.replace("_", " ").title(),
            "Reach "
            f"{definition.threshold} "
            f"{definition.criterion.value.replace('_', ' ')}.",
        )
        for definition in ACHIEVEMENT_DEFINITIONS
        if definition.id.value not in ACHIEVEMENT_PRESENTATION
    }
)


@dataclass(frozen=True, slots=True)
class AchievementStatus:
    achievement_id: str
    name: str
    description: str
    progress: int
    threshold: int
    configured_reward: int
    unlocked_at: object | None
    rewarded_candies: CandyBundle | None
    rewarded_mints: int = 0
    family: str = "Capture"
    configured_mints: int = 0

    @property
    def unlocked(self) -> bool:
        return self.unlocked_at is not None


class AchievementQueryService:
    """Read-only achievement status projection."""

    def __init__(self, activity_repository, unlock_repository) -> None:
        self._activity_repository = activity_repository
        self._unlock_repository = unlock_repository

    async def get_for_trainer(self, trainer_id: int) -> tuple[AchievementStatus, ...]:
        progress = await self._activity_repository.get_progress(trainer_id)
        unlocks = {
            unlock.achievement_id: unlock
            for unlock in await self._unlock_repository.get_by_trainer(trainer_id)
        }
        result = []
        for definition in ACHIEVEMENT_DEFINITIONS:
            name, description = ACHIEVEMENT_PRESENTATION[definition.id.value]
            unlock = unlocks.get(definition.id.value)
            result.append(
                AchievementStatus(
                    definition.id.value,
                    name,
                    description,
                    self._progress(progress, definition.criterion, definition.scope),
                    definition.threshold,
                    definition.reward_amount,
                    unlock.unlocked_at if unlock else None,
                    unlock.rewarded_candies if unlock else None,
                    unlock.rewarded_mints if unlock else 0,
                    self._family(definition.criterion),
                    definition.mint_reward,
                )
            )
        return tuple(result)

    @staticmethod
    def _progress(progress, criterion: AchievementCriterion, scope=None) -> int:
        if criterion is AchievementCriterion.TYPE_CAPTURE_COUNT:
            return progress.capture_counts_by_type.get(scope or "", 0)
        return {
            AchievementCriterion.CAPTURE_COUNT: progress.capture_count,
            AchievementCriterion.SHINY_CAPTURE_COUNT: progress.shiny_capture_count,
            AchievementCriterion.UNIQUE_DISCOVERED_SPECIES: (
                progress.unique_discovered_species
            ),
            AchievementCriterion.COMPLETED_TRADE_COUNT: progress.completed_trade_count,
            AchievementCriterion.SAFARI_CAPTURE_COUNT: progress.safari_capture_count,
            AchievementCriterion.LEGENDARY_CAPTURE_COUNT: (
                progress.legendary_capture_count
            ),
            AchievementCriterion.MYTHICAL_CAPTURE_COUNT: (
                progress.mythical_capture_count
            ),
            AchievementCriterion.BABY_CAPTURE_COUNT: progress.baby_capture_count,
        }[criterion]

    @staticmethod
    def _family(criterion: AchievementCriterion) -> str:
        return {
            AchievementCriterion.CAPTURE_COUNT: "Capture",
            AchievementCriterion.UNIQUE_DISCOVERED_SPECIES: "Pokédex",
            AchievementCriterion.SHINY_CAPTURE_COUNT: "Shiny",
            AchievementCriterion.SAFARI_CAPTURE_COUNT: "Safari",
            AchievementCriterion.COMPLETED_TRADE_COUNT: "Trade",
            AchievementCriterion.TYPE_CAPTURE_COUNT: "Types",
        }.get(criterion, "Special")
