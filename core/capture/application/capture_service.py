from core.candy.candy_bundle import CandyBundle
from core.candy.candy_repository import CandyRepository
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_application_result import (
    CaptureApplicationResult,
)
from core.capture.service import CaptureService
from core.creature.creature_repository import CreatureRepository
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
        creature_repository: CreatureRepository,
        candy_repository: CandyRepository,
        reward_policy: RewardPolicy,
        spawn_session_repository: SpawnSessionRepository,
    ) -> None:
        self._capture_service = capture_service
        self._creature_repository = creature_repository
        self._candy_repository = candy_repository
        self._reward_policy = reward_policy
        self._spawn_session_repository = spawn_session_repository

    async def capture(
        self,
        trainer_id: int,
        guild_id: int,
    ) -> CaptureApplicationResult:
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

        creature = await self._creature_repository.save(
            result.creature,
        )

        reward = self._reward_policy.reward_for(
            creature,
        )

        inventory = await self._candy_repository.get(
            trainer_id,
        )

        inventory.add(
            reward,
        )

        await self._candy_repository.save(
            trainer_id,
            inventory,
        )

        await self._spawn_session_repository.clear(
            guild_id,
        )

        return CaptureApplicationResult(
            attempt=result.attempt,
            success=True,
            creature=creature,
            reward=reward,
        )
