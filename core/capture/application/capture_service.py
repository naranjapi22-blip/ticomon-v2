import logging
from collections.abc import Callable
from datetime import UTC, datetime

from core.achievement.activity import (
    AchievementActivity,
    AchievementActivityType,
    AchievementSource,
)
from core.candy.candy_bundle import CandyBundle
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_application_result import (
    CaptureApplicationResult,
)
from core.capture.application.capture_unit_of_work import CaptureUnitOfWork
from core.capture.service import CaptureService
from core.collection.history import CollectionEntrySource
from core.safari.daily_progress import SafariDailyProgressService
from core.spawn.exceptions import (
    NoActiveSpawnSession,
    NoSelectedOpportunity,
)
from core.spawn.spawn_session_repository import SpawnSessionRepository


class CaptureApplicationService:
    """
    Executes the complete capture use case.
    """

    def __init__(
        self,
        capture_service: CaptureService,
        unit_of_work: CaptureUnitOfWork,
        reward_policy: RewardPolicy,
        spawn_session_repository: SpawnSessionRepository,
        daily_progress_service: SafariDailyProgressService | None = None,
        clock: Callable[[], datetime] | None = None,
        achievement_award_service=None,
    ) -> None:
        self._capture_service = capture_service
        self._unit_of_work = unit_of_work
        self._reward_policy = reward_policy
        self._daily_progress_service = (
            daily_progress_service or SafariDailyProgressService()
        )
        self._spawn_session_repository = spawn_session_repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._achievement_award_service = achievement_award_service

    async def capture(
        self,
        trainer_id: int,
        guild_id: int,
    ) -> CaptureApplicationResult:

        async with self._spawn_session_repository.lock(guild_id):

            session = await self._spawn_session_repository.get_active(
                guild_id,
            )

            if session is None:
                raise NoActiveSpawnSession()

            if session.selected_opportunity is None:
                raise NoSelectedOpportunity()

            result = self._capture_service.capture(
                trainer_id=trainer_id,
                opportunity=session.selected_opportunity,
            )

            if not result.success:
                return CaptureApplicationResult(
                    attempt=result.attempt,
                    success=False,
                    creature=None,
                    reward=CandyBundle(),
                )

            assert result.creature is not None

            reward = self._reward_policy.reward_for(
                result.creature,
            )
            captured_at = self._clock()

            async with self._unit_of_work.transaction() as transaction:
                creature = await transaction.save_creature(result.creature)
                await transaction.record_collection_entry(
                    creature,
                    CollectionEntrySource.CAPTURE,
                )
                inventory = await transaction.get_candy_inventory(trainer_id)
                inventory.add(reward)
                await transaction.save_candy_inventory(trainer_id, inventory)
                await self._record_activities(
                    transaction,
                    creature,
                    AchievementSource.NORMAL,
                )

                cycle_date = captured_at.date()
                daily_world = await transaction.get_or_create_daily_world(
                    guild_id,
                    cycle_date,
                )
                await transaction.expire_available_unlocks_before(
                    guild_id,
                    cycle_date,
                )
                await transaction.register_daily_active_trainer_if_absent(
                    guild_id,
                    cycle_date,
                    trainer_id,
                    captured_at,
                )
                active_player_count = await transaction.count_daily_active_trainers(
                    guild_id,
                    cycle_date,
                )
                progress = self._daily_progress_service.register_capture(
                    world=daily_world,
                    species_types=creature.species.types,
                    captured_at=captured_at,
                    active_player_count=active_player_count,
                )
                await transaction.save_daily_world(progress.world)

                for unlock in progress.created_unlocks:
                    await transaction.save_unlock(unlock)

            achievements = await self._award(creature, is_safari=False)
            await self._spawn_session_repository.clear(guild_id)
            return CaptureApplicationResult(
                attempt=result.attempt,
                success=True,
                creature=creature,
                reward=reward,
                achievements=achievements,
            )

    @staticmethod
    async def _record_activities(
        transaction,
        creature,
        source: AchievementSource,
    ) -> None:
        key = f"creature:{creature.id}"
        activities = [
            AchievementActivity(
                trainer_id=creature.trainer_id,
                activity_type=AchievementActivityType.CAPTURE,
                idempotency_key=key,
                species_id=creature.species.id,
                source=source,
            ),
            AchievementActivity(
                trainer_id=creature.trainer_id,
                activity_type=AchievementActivityType.SPECIES_DISCOVERED,
                idempotency_key=key,
                species_id=creature.species.id,
                source=source,
            ),
        ]
        if creature.is_shiny:
            activities.append(
                AchievementActivity(
                    trainer_id=creature.trainer_id,
                    activity_type=AchievementActivityType.SHINY_CAPTURE,
                    idempotency_key=key,
                    species_id=creature.species.id,
                    source=source,
                )
            )
        for activity in activities:
            await transaction.record_achievement_activity(activity)

    async def _award(self, creature, *, is_safari: bool):
        if self._achievement_award_service is None:
            return ()
        try:
            return await self._achievement_award_service.award_for_capture(
                creature.trainer_id,
                creature.species,
                is_shiny=creature.is_shiny,
                is_safari=is_safari,
            )
        except Exception:
            logging.getLogger(__name__).exception(
                "achievement award failed trainer_id=%s creature_id=%s",
                creature.trainer_id,
                creature.id,
            )
            return ()
