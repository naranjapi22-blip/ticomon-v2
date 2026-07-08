import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from core.spawn.application.spawn_service import SpawnService
from core.spawn.context import SpawnContext
from core.spawn.profile import SpawnProfile
from core.spawn.region import Region
from core.spawn.session import SpawnSession
from core.spawn.spawn_session_repository import SpawnSessionRepository
from core.spawn.world import World


class SpawnAlreadyActive(Exception):
    """Raised when a command spawn is already active."""


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
        self._locks: defaultdict[int, asyncio.Lock] = defaultdict(
            asyncio.Lock,
        )

    async def spawn(
        self,
        guild_id: int,
        owner_id: int,
    ) -> SpawnSession:
        async with self._locks[guild_id]:
            active = await self._spawn_session_repository.get_active(
                guild_id,
            )

            if active is not None:
                expired = (datetime.utcnow() - active.created_at) >= timedelta(
                    minutes=5
                )

                if not expired:
                    raise SpawnAlreadyActive()

                await self._spawn_session_repository.clear(
                    guild_id,
                )

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
                owner_id=owner_id,
                opportunities=list(opportunities),
            )

            await self._spawn_session_repository.save(
                guild_id,
                session,
            )

            return session
