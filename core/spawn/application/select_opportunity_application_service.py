from core.opportunity.opportunity import Opportunity
from core.spawn.exceptions import NoActiveSpawnSession
from core.spawn.spawn_session_repository import (
    SpawnSessionRepository,
)


class SelectOpportunityApplicationService:
    """
    Executes the opportunity selection use case.
    """

    def __init__(
        self,
        spawn_session_repository: SpawnSessionRepository,
    ) -> None:
        self._spawn_session_repository = spawn_session_repository

    async def select_opportunity(
        self,
        guild_id: int,
        opportunity_index: int,
    ) -> Opportunity:
        session = await self._spawn_session_repository.get_active(
            guild_id,
        )

        if session is None:
            raise NoActiveSpawnSession()

        return session.select_opportunity(
            opportunity_index,
        )
