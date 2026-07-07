from core.spawn.application.spawn_service import SpawnService
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.session import SpawnSession
from core.spawn.spawn_session_repository import (
    SpawnSessionRepository,
)
from core.spawn.world import World


class SpawnApplicationService:
    """
    Application use case responsible for executing a spawn.
    """

    def __init__(
        self,
        spawn_service: SpawnService,
        spawn_session_repository: SpawnSessionRepository,
    ) -> None:
        self._spawn_service = spawn_service
        self._spawn_session_repository = spawn_session_repository

    async def spawn(self) -> SpawnSession:
        context = SpawnContext(
            world=World.MAIN,
            region=Region.KANTO,
        )

        profile = SpawnProfile(
            opportunity_count=3,
        )

        opportunities = await self._spawn_service.spawn(
            context=context,
            profile=profile,
        )

        session = SpawnSession(
            opportunities=list(opportunities),
        )

        await self._spawn_session_repository.save(session)

        return session
