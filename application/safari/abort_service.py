from __future__ import annotations

import logging
from dataclasses import dataclass

from application.safari.activity_state import SafariActivityTracker
from application.safari.exceptions import SafariActivityNotFound
from core.safari.activity_repository import SafariActivityRepository
from core.safari.registration import SafariRegistration
from core.safari.session import SafariSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AbortSafariResult:
    activity: SafariRegistration | SafariSession


class AbortSafariApplicationService:
    def __init__(
        self,
        activity_repository: SafariActivityRepository,
        activity_tracker: SafariActivityTracker,
    ) -> None:
        self._activity_repository = activity_repository
        self._activity_tracker = activity_tracker

    async def abort(
        self,
        guild_id: int,
        trainer_id: int,
    ) -> AbortSafariResult:
        async with self._activity_repository.lock(guild_id):
            activity = await self._activity_repository.get_activity(guild_id)
            if activity is None:
                raise SafariActivityNotFound("Safari activity was not found.")

            if isinstance(activity, SafariSession):
                await self._activity_repository.clear_session(guild_id)
                session_id = activity.id
            else:
                await self._activity_repository.clear_registration(guild_id)
                session_id = None

            self._activity_tracker.clear(guild_id)
            logger.warning(
                "safari_aborted guild_id=%s session_id=%s trainer_id=%s",
                guild_id,
                session_id,
                trainer_id,
            )
            return AbortSafariResult(activity=activity)
