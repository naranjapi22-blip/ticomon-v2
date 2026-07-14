from __future__ import annotations

from application.safari.activity_state import SafariActivityTracker
from application.safari.results import SafariActivitySnapshot
from core.safari.activity_repository import SafariActivityRepository


class GetSafariActivityApplicationService:
    def __init__(
        self,
        activity_repository: SafariActivityRepository,
        activity_tracker: SafariActivityTracker,
    ) -> None:
        self._activity_repository = activity_repository
        self._activity_tracker = activity_tracker

    async def get(self, guild_id: int) -> SafariActivitySnapshot | None:
        activity = await self._activity_repository.get_activity(guild_id)
        if activity is None:
            return None

        return SafariActivitySnapshot(
            activity=activity,
            timing=self._activity_tracker.get(guild_id),
        )
