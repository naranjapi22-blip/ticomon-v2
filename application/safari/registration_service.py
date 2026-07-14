import logging
from datetime import datetime

from application.safari.activity_state import SafariActivityTracker
from application.safari.exceptions import (
    SafariActivityAlreadyExists,
    SafariRegistrationNotFound,
    SafariUnlockUnavailable,
)
from application.safari.results import (
    CancelSafariRegistrationResult,
    JoinSafariRegistrationResult,
    OpenSafariRegistrationResult,
)
from core.safari.activity_repository import SafariActivityRepository
from core.safari.registration import SafariRegistration
from core.safari.unlock_repository import SafariUnlockRepository

logger = logging.getLogger(__name__)


class SafariRegistrationApplicationService:
    def __init__(
        self,
        activity_repository: SafariActivityRepository,
        unlock_repository: SafariUnlockRepository,
        activity_tracker: SafariActivityTracker,
    ) -> None:
        self._activity_repository = activity_repository
        self._unlock_repository = unlock_repository
        self._activity_tracker = activity_tracker

    async def open(
        self,
        guild_id: int,
        trainer_id: int,
        opened_at: datetime,
    ) -> OpenSafariRegistrationResult:
        async with self._activity_repository.lock(guild_id):
            if await self._activity_repository.get_activity(guild_id) is not None:
                raise SafariActivityAlreadyExists(
                    "Safari activity already exists for guild."
                )

            unlocks = await self._unlock_repository.get_available_by_guild_id(guild_id)
            if not unlocks:
                raise SafariUnlockUnavailable("No Safari unlock is available.")
            unlock = unlocks[0]
            if unlock.id is None:
                raise SafariUnlockUnavailable(
                    "Available Safari unlock has no identity."
                )

            registration = SafariRegistration(
                guild_id=guild_id,
                unlock_id=unlock.id,
                participant_ids=(trainer_id,),
                opened_at=opened_at,
            )
            await self._activity_repository.save_registration(registration)
            logger.info(
                "safari_registration_opened guild_id=%s unlock_id=%s trainer_id=%s "
                "participant_count=%s",
                guild_id,
                unlock.id,
                trainer_id,
                registration.participant_count,
            )
            return OpenSafariRegistrationResult(
                registration=registration,
                unlock=unlock,
                level=unlock.level,
                encounter_count=unlock.encounter_count,
                balls_per_participant=unlock.balls_per_participant,
            )

    async def join(
        self,
        guild_id: int,
        trainer_id: int,
    ) -> JoinSafariRegistrationResult:
        async with self._activity_repository.lock(guild_id):
            registration = await self._activity_repository.get_registration(guild_id)
            if registration is None:
                raise SafariRegistrationNotFound("Safari registration was not found.")

            already_registered = trainer_id in registration.participant_ids
            registration.join(trainer_id)
            logger.debug(
                "safari_participant_joined guild_id=%s trainer_id=%s added=%s "
                "participant_count=%s",
                guild_id,
                trainer_id,
                not already_registered,
                registration.participant_count,
            )
            return JoinSafariRegistrationResult(
                added=not already_registered,
                participant_count=registration.participant_count,
                status=registration.status,
            )

    async def cancel(
        self,
        guild_id: int,
    ) -> CancelSafariRegistrationResult:
        async with self._activity_repository.lock(guild_id):
            registration = await self._activity_repository.get_registration(guild_id)
            if registration is None:
                raise SafariRegistrationNotFound("Safari registration was not found.")

            registration.cancel()
            await self._activity_repository.clear_registration(guild_id)
            self._activity_tracker.clear(guild_id)
            logger.info("safari_registration_cancelled guild_id=%s", guild_id)
            return CancelSafariRegistrationResult(registration)
