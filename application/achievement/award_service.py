from datetime import UTC, datetime

from application.achievement.contracts import AchievementProgress
from core.achievement.definition import (
    ACHIEVEMENT_DEFINITIONS,
    AchievementCriterion,
    AchievementId,
)
from core.achievement.reward_policy import AchievementRewardPolicy
from core.achievement.unlock_result import AchievementUnlockResult
from core.species.species import Species


class CaptureAchievementAwardService:
    """Awards only milestones that a successful capture can affect."""

    def __init__(self, activity_repository, unlock_repository) -> None:
        self._activity_repository = activity_repository
        self._unlock_repository = unlock_repository
        self._reward_policy = AchievementRewardPolicy()

    async def award_for_capture(
        self,
        trainer_id: int,
        species: Species,
        *,
        is_shiny: bool,
        is_safari: bool,
    ) -> tuple[AchievementUnlockResult, ...]:
        progress = await self._activity_repository.get_progress(trainer_id)
        definitions = self._affected_definitions(is_shiny, is_safari)
        awarded: list[AchievementUnlockResult] = []
        for definition in definitions:
            if self._value(progress, definition.criterion) < definition.threshold:
                continue
            reward = self._reward_policy.reward_for(species, definition.reward_amount)
            if await self._unlock_repository.award(
                trainer_id,
                definition.id.value,
                reward,
                datetime.now(UTC),
            ):
                awarded.append(AchievementUnlockResult(definition.id.value, reward))
        return tuple(awarded)

    @staticmethod
    def _affected_definitions(
        is_shiny: bool,
        is_safari: bool,
    ) -> tuple:
        ids = {
            AchievementId.FIRST_CAPTURE,
            AchievementId.CAPTURES_10,
            AchievementId.CAPTURES_50,
            AchievementId.UNIQUE_SPECIES_10,
        }
        if is_shiny:
            ids.add(AchievementId.FIRST_SHINY_CAPTURE)
        if is_safari:
            ids.add(AchievementId.FIRST_SAFARI_CAPTURE)
        return tuple(item for item in ACHIEVEMENT_DEFINITIONS if item.id in ids)

    @staticmethod
    def _value(progress: AchievementProgress, criterion: AchievementCriterion) -> int:
        return {
            AchievementCriterion.CAPTURE_COUNT: progress.capture_count,
            AchievementCriterion.SHINY_CAPTURE_COUNT: progress.shiny_capture_count,
            AchievementCriterion.UNIQUE_DISCOVERED_SPECIES: (
                progress.unique_discovered_species
            ),
            AchievementCriterion.SAFARI_CAPTURE_COUNT: progress.safari_capture_count,
        }.get(criterion, 0)
