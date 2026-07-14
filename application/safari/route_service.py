from __future__ import annotations

import logging
import random
from datetime import datetime

from application.safari.exceptions import (
    SafariRouteVoteNotFound,
    SafariRouteVoteUnavailable,
    SafariSessionNotFound,
)
from application.safari.results import (
    CastSafariRouteVoteResult,
    OpenSafariRouteVoteResult,
    ResolveSafariRouteVoteResult,
)
from core.safari.activity_repository import SafariActivityRepository
from core.safari.domain import SAFARI_ZONE_DEFINITION_BY_ZONE, SafariComposition
from core.safari.encounter_context import SafariEncounterContext
from core.safari.encounter_generator import SafariEncounterGenerator
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.route import SafariRouteOption
from core.safari.route_option_factory import SafariRouteOptionFactory
from core.safari.route_vote import SafariRouteVote
from core.safari.session import SafariSession, SafariSessionStatus

logger = logging.getLogger(__name__)


class SafariRouteApplicationService:
    def __init__(
        self,
        activity_repository: SafariActivityRepository,
        route_option_factory: SafariRouteOptionFactory,
        encounter_generator: SafariEncounterGenerator,
        random_source: random.Random,
    ) -> None:
        self._activity_repository = activity_repository
        self._route_option_factory = route_option_factory
        self._encounter_generator = encounter_generator
        self._random_source = random_source

    async def open_route_vote(
        self,
        guild_id: int,
        opened_at: datetime,
    ) -> OpenSafariRouteVoteResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            self._require_route_decision(session)

            previous_option = self._previous_route_option(session)
            options = self._route_option_factory.create_options(
                current_zone=session.current_segment.zone,
                visited_zones=tuple(segment.zone for segment in session.route_segments),
                previous_option=previous_option,
                random_source=self._random_source,
            )
            vote = SafariRouteVote(options, opened_at)
            session.start_route_vote(vote)
            await self._activity_repository.save_session(session)
            logger.info(
                "safari_route_vote_opened guild_id=%s session_id=%s options=%s",
                guild_id,
                session.id,
                len(vote.options),
            )
            return OpenSafariRouteVoteResult(
                session=session,
                vote=vote,
                options=tuple(vote.options),
            )

    async def cast_route_vote(
        self,
        guild_id: int,
        trainer_id: int,
        option_id: str,
    ) -> CastSafariRouteVoteResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            vote = self._require_current_vote(session)
            replaced = trainer_id in vote.votes_by_trainer
            session.cast_route_vote(trainer_id, option_id)
            await self._activity_repository.save_session(session)
            logger.debug(
                "safari_route_vote_cast guild_id=%s session_id=%s trainer_id=%s "
                "option_id=%s replaced=%s",
                guild_id,
                session.id,
                trainer_id,
                option_id,
                replaced,
            )
            return CastSafariRouteVoteResult(
                session=session,
                vote=vote,
                trainer_id=trainer_id,
                option_id=option_id,
                replaced=replaced,
            )

    async def resolve_route_vote(
        self,
        guild_id: int,
    ) -> ResolveSafariRouteVoteResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            self._require_current_vote(session)

            vote_result = session.resolve_route_vote(self._random_source)
            next_encounter = await self._generate_next_encounter(session)
            session.publish_encounter(next_encounter.encounter)
            await self._activity_repository.save_session(session)
            logger.info(
                "safari_route_resolved guild_id=%s session_id=%s selected_option=%s",
                guild_id,
                session.id,
                vote_result.selected_option.id,
            )
            return ResolveSafariRouteVoteResult(
                session=session,
                vote_result=vote_result,
                selected_option=vote_result.selected_option,
                destination_segment=session.current_segment,
                next_encounter=next_encounter,
            )

    async def _require_session(self, guild_id: int) -> SafariSession:
        session = await self._activity_repository.get_session(guild_id)
        if session is None:
            raise SafariSessionNotFound("Safari session was not found.")
        return session

    @staticmethod
    def _require_route_decision(session: SafariSession) -> None:
        if session.status is not SafariSessionStatus.ROUTE_DECISION:
            raise SafariRouteVoteUnavailable("Safari route vote is not available.")
        if session.current_route_vote is not None:
            raise SafariRouteVoteUnavailable("Safari route vote is already open.")
        if (
            session.current_encounter is not None
            or not session.current_segment.is_complete
        ):
            raise SafariRouteVoteUnavailable("Safari route vote is not available.")

    @staticmethod
    def _require_current_vote(session: SafariSession) -> SafariRouteVote:
        if session.status is not SafariSessionStatus.ROUTE_DECISION:
            raise SafariRouteVoteNotFound("Safari route vote was not found.")
        vote = session.current_route_vote
        if vote is None:
            raise SafariRouteVoteNotFound("Safari route vote was not found.")
        return vote

    @staticmethod
    def _previous_route_option(session: SafariSession) -> SafariRouteOption | None:
        if len(session.route_segments) < 2:
            return None

        previous_segment = session.route_segments[-2]
        current_segment = session.route_segments[-1]
        if current_segment.source_option_id is None:
            return None

        destination_definition = SAFARI_ZONE_DEFINITION_BY_ZONE[current_segment.zone]
        return SafariRouteOption(
            id=current_segment.source_option_id,
            source_zone=previous_segment.zone,
            destination_zone=current_segment.zone,
            type_weight_modifiers=destination_definition.base_type_weights,
            allowed_events=destination_definition.allowed_events,
            narrative_key=(
                f"{previous_segment.zone.value.lower()}_to_"
                f"{current_segment.zone.value.lower()}"
            ),
        )

    async def _generate_next_encounter(
        self,
        session: SafariSession,
    ) -> SafariGeneratedEncounter:
        current_segment = session.current_segment
        definition = SAFARI_ZONE_DEFINITION_BY_ZONE[current_segment.zone]
        context = SafariEncounterContext(
            safari_map=session.safari_map,
            zone=current_segment.zone,
            weather=session.weather,
            time_of_day=session.time_of_day,
            phase=session.phase,
            map_type_weight_modifiers={},
            zone_type_weight_modifiers=definition.base_type_weights,
            route_type_weight_modifiers=current_segment.type_weight_modifiers,
            seen_species_ids=session.seen_species_ids,
            route_allowed_events=frozenset(current_segment.allowed_events),
            extraordinary_flags=session.extraordinary_flags,
        )
        return await self._encounter_generator.generate_with_events(
            context,
            (SafariComposition.NORMAL,),
        )
