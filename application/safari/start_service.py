import logging
from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from application.safari.exceptions import (
    SafariInsufficientParticipants,
    SafariInvalidUnlockConfiguration,
    SafariRegistrationNotFound,
    SafariUnlockUnavailable,
)
from application.safari.results import StartSafariResult
from core.safari.activity_repository import SafariActivityRepository
from core.safari.domain import (
    SAFARI_INITIAL_ZONE_BY_MAP,
    SAFARI_LEVEL_CONFIGS,
    SAFARI_MAX_PARTICIPANTS,
    SAFARI_MIN_PARTICIPANTS,
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariComposition,
    SafariRegistrationStatus,
)
from core.safari.encounter_context import SafariEncounterContext
from core.safari.encounter_generator import SafariEncounterGenerator
from core.safari.map_selector import SafariMapSelector
from core.safari.participant import SafariParticipant
from core.safari.registration import (
    SafariParticipantLimitReached,
    SafariRegistrationClosed,
)
from core.safari.route import SafariRouteSegment
from core.safari.route_schedule import SafariRouteSchedulePolicy
from core.safari.session import SafariSession
from core.safari.time_of_day_selector import SafariTimeOfDaySelector
from core.safari.unlock import SafariUnlock
from core.safari.unlock_repository import SafariUnlockRepository
from core.safari.weather_selector import SafariWeatherSelector

logger = logging.getLogger(__name__)


class StartSafariApplicationService:
    def __init__(
        self,
        activity_repository: SafariActivityRepository,
        unlock_repository: SafariUnlockRepository,
        map_selector: SafariMapSelector,
        weather_selector: SafariWeatherSelector,
        time_of_day_selector: SafariTimeOfDaySelector,
        encounter_generator: SafariEncounterGenerator,
        random_source,
        session_id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._activity_repository = activity_repository
        self._unlock_repository = unlock_repository
        self._map_selector = map_selector
        self._weather_selector = weather_selector
        self._time_of_day_selector = time_of_day_selector
        self._encounter_generator = encounter_generator
        self._random_source = random_source
        self._session_id_factory = session_id_factory

    async def start(
        self,
        guild_id: int,
        started_at: datetime,
    ) -> StartSafariResult:
        return await self._start(
            guild_id,
            started_at,
            minimum_participants=SAFARI_MIN_PARTICIPANTS,
        )

    async def start_for_testing(
        self,
        guild_id: int,
        started_at: datetime,
    ) -> StartSafariResult:
        return await self._start(
            guild_id,
            started_at,
            minimum_participants=1,
        )

    async def _start(
        self,
        guild_id: int,
        started_at: datetime,
        *,
        minimum_participants: int,
    ) -> StartSafariResult:
        async with self._activity_repository.lock(guild_id):
            registration = await self._activity_repository.get_registration(guild_id)
            if registration is None:
                raise SafariRegistrationNotFound("Safari registration was not found.")
            if registration.status is not SafariRegistrationStatus.OPEN:
                raise SafariRegistrationClosed("Safari registration is closed.")
            if registration.participant_count > SAFARI_MAX_PARTICIPANTS:
                raise SafariParticipantLimitReached(
                    "Safari registration participant limit exceeded."
                )
            if not registration.has_minimum(minimum_participants):
                raise SafariInsufficientParticipants(
                    "Safari requires at least two participants."
                    if minimum_participants > 1
                    else "Safari requires at least one participant."
                )

            unlock = await self._available_registered_unlock(registration)
            session_id = self._session_id_factory()
            session, generated = await self._build_session(
                registration=registration,
                unlock=unlock,
                session_id=session_id,
                started_at=started_at,
            )

            consumed_unlock = await self._unlock_repository.consume(
                unlock_id=registration.unlock_id,
                guild_id=guild_id,
                consumed_at=started_at,
                consumed_session_id=session_id,
            )
            if consumed_unlock is None:
                raise SafariUnlockUnavailable(
                    "The Safari unlock reserved by this registration is unavailable."
                )

            logger.info(
                "safari_unlocked guild_id=%s unlock_id=%s session_id=%s level=%s "
                "encounter_count=%s participants=%s",
                guild_id,
                consumed_unlock.id,
                session.id,
                session.level,
                session.total_encounters,
                len(session.participants_by_trainer),
            )

            try:
                await self._activity_repository.save_session(session)
            except Exception:
                logger.exception(
                    "failed to persist safari session after unlock consumption "
                    "guild_id=%s session_id=%s unlock_id=%s",
                    guild_id,
                    session.id,
                    consumed_unlock.id,
                )
                raise

            registration.consume()
            logger.info(
                "safari_started guild_id=%s session_id=%s unlock_id=%s "
                "participants=%s encounter_count=%s level=%s",
                guild_id,
                session.id,
                consumed_unlock.id,
                len(session.participants_by_trainer),
                session.total_encounters,
                session.level,
            )
            return StartSafariResult(session, consumed_unlock, generated)

    async def _available_registered_unlock(
        self,
        registration,
    ) -> SafariUnlock:
        unlocks = await self._unlock_repository.get_available_by_guild_id(
            registration.guild_id
        )
        unlock = next(
            (item for item in unlocks if item.id == registration.unlock_id),
            None,
        )
        if unlock is None:
            raise SafariUnlockUnavailable(
                "The Safari unlock reserved by this registration is unavailable."
            )
        self._validate_unlock_configuration(unlock)
        return unlock

    async def _build_session(
        self,
        registration,
        unlock: SafariUnlock,
        session_id: UUID,
        started_at: datetime,
    ):
        safari_map = self._map_selector.select(
            unlock.map_influence,
            self._random_source,
        )
        weather = self._weather_selector.select(safari_map, self._random_source)
        time_of_day = self._time_of_day_selector.select(self._random_source)
        zone = SAFARI_INITIAL_ZONE_BY_MAP[safari_map]
        definition = SAFARI_ZONE_DEFINITION_BY_ZONE[zone]
        initial_length = SafariRouteSchedulePolicy().segment_length_for(
            unlock.encounter_count,
            0,
        )
        segment = SafariRouteSegment(
            zone=zone,
            remaining_encounters=initial_length,
            type_weight_modifiers=definition.base_type_weights,
            allowed_events=definition.allowed_events,
        )
        participants = tuple(
            SafariParticipant(
                trainer_id=trainer_id,
                initial_balls=unlock.balls_per_participant,
                remaining_balls=unlock.balls_per_participant,
            )
            for trainer_id in sorted(registration.participant_ids)
        )
        session = SafariSession(
            id=session_id,
            guild_id=registration.guild_id,
            participants=participants,
            total_encounters=unlock.encounter_count,
            initial_segment=segment,
            started_at=started_at,
            unlock_id=registration.unlock_id,
            level=unlock.level,
            safari_map=safari_map,
            weather=weather,
            time_of_day=time_of_day,
        )
        context = SafariEncounterContext(
            safari_map=safari_map,
            zone=zone,
            weather=weather,
            time_of_day=time_of_day,
            phase=session.phase,
            map_type_weight_modifiers={},
            zone_type_weight_modifiers=definition.base_type_weights,
            route_type_weight_modifiers=segment.type_weight_modifiers,
            route_allowed_events=frozenset(segment.allowed_events),
            seen_species_ids=session.seen_species_ids,
            extraordinary_flags=session.extraordinary_flags,
        )
        generated = await self._encounter_generator.generate_with_events(
            context,
            (SafariComposition.NORMAL,),
        )
        session.publish_encounter(generated.encounter)
        return session, generated

    @staticmethod
    def _validate_unlock_configuration(unlock: SafariUnlock) -> None:
        configuration = SAFARI_LEVEL_CONFIGS.get(unlock.level)
        if configuration is None or (
            configuration.encounter_count != unlock.encounter_count
            or configuration.balls_per_participant != unlock.balls_per_participant
        ):
            raise SafariInvalidUnlockConfiguration(
                "Safari unlock configuration does not match its level."
            )
