from datetime import UTC, datetime

from application.achievement.contracts import AchievementProgress
from core.achievement.definition import (
    ACHIEVEMENT_DEFINITIONS,
    AchievementCriterion,
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
            if (
                self._value(progress, definition.criterion, definition.scope)
                < definition.threshold
            ):
                continue
            reward = self._reward_policy.reward_for(species, definition.reward_amount)
            if await self._unlock_repository.award(
                trainer_id,
                definition.id.value,
                reward,
                datetime.now(UTC),
                definition.mint_reward,
            ):
                awarded.append(
                    AchievementUnlockResult(
                        definition.id.value, reward, definition.mint_reward
                    )
                )
        return tuple(awarded)

    async def award_for_completed_trade(
        self,
        trainer_id: int,
        species: Species,
    ) -> tuple[AchievementUnlockResult, ...]:
        progress = await self._activity_repository.get_progress(trainer_id)
        awarded_results: list[AchievementUnlockResult] = []
        for definition in ACHIEVEMENT_DEFINITIONS:
            if definition.criterion is not AchievementCriterion.COMPLETED_TRADE_COUNT:
                continue
            if (
                self._value(progress, definition.criterion, definition.scope)
                < definition.threshold
            ):
                continue
            reward = self._reward_policy.reward_for(species, definition.reward_amount)
            if await self._unlock_repository.award(
                trainer_id,
                definition.id.value,
                reward,
                datetime.now(UTC),
                definition.mint_reward,
            ):
                awarded_results.append(
                    AchievementUnlockResult(
                        definition.id.value, reward, definition.mint_reward
                    )
                )
        return tuple(awarded_results)

    @staticmethod
    def _affected_definitions(
        is_shiny: bool,
        is_safari: bool,
    ) -> tuple:
        criteria = {
            AchievementCriterion.CAPTURE_COUNT,
            AchievementCriterion.UNIQUE_DISCOVERED_SPECIES,
            AchievementCriterion.LEGENDARY_CAPTURE_COUNT,
            AchievementCriterion.MYTHICAL_CAPTURE_COUNT,
            AchievementCriterion.BABY_CAPTURE_COUNT,
            AchievementCriterion.TYPE_CAPTURE_COUNT,
        }
        if is_shiny:
            criteria.add(AchievementCriterion.SHINY_CAPTURE_COUNT)
        if is_safari:
            criteria.add(AchievementCriterion.SAFARI_CAPTURE_COUNT)
        return tuple(
            item for item in ACHIEVEMENT_DEFINITIONS if item.criterion in criteria
        )

    @staticmethod
    def _value(
        progress: AchievementProgress, criterion: AchievementCriterion, scope=None
    ) -> int:
        values = {
            AchievementCriterion.CAPTURE_COUNT: progress.capture_count,
            AchievementCriterion.SHINY_CAPTURE_COUNT: progress.shiny_capture_count,
            AchievementCriterion.UNIQUE_DISCOVERED_SPECIES: (
                progress.unique_discovered_species
            ),
            AchievementCriterion.SAFARI_CAPTURE_COUNT: progress.safari_capture_count,
            AchievementCriterion.COMPLETED_TRADE_COUNT: progress.completed_trade_count,
            AchievementCriterion.LEGENDARY_CAPTURE_COUNT: (
                progress.legendary_capture_count
            ),
            AchievementCriterion.MYTHICAL_CAPTURE_COUNT: (
                progress.mythical_capture_count
            ),
            AchievementCriterion.BABY_CAPTURE_COUNT: progress.baby_capture_count,
        }
        if criterion is AchievementCriterion.TYPE_CAPTURE_COUNT:
            return progress.capture_counts_by_type.get(scope or "", 0)
        return values.get(criterion, 0)
