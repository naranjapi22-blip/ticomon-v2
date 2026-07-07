from core.spawn.application.spawn_service import SpawnService
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.world import World


class SpawnApplicationService:
    """
    Application use case responsible for executing a spawn.
    """

    def __init__(
        self,
        spawn_service: SpawnService,
    ) -> None:
        self._spawn_service = spawn_service

    async def spawn(self):
        context = SpawnContext(
            world=World.MAIN,
            region=Region.KANTO,
        )

        profile = SpawnProfile(
            opportunity_count=3,
        )

        return await self._spawn_service.spawn(
            context=context,
            profile=profile,
        )
