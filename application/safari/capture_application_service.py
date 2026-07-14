from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

from application.safari.exceptions import (
    SafariCaptureResolutionUnavailable,
    SafariCaptureSelectionNotFound,
    SafariCaptureSelectionUnavailable,
    SafariSessionNotFound,
)
from application.safari.results import (
    CloseSafariCaptureSelectionResult,
    ConfirmSafariCaptureSelectionResult,
    DeclineSafariCaptureResult,
    ResolveSafariCaptureResult,
    SafariCaptureSelectionState,
    SafariCaptureSlotApplicationResult,
    SelectSafariCaptureResult,
)
from core.candy.candy_bundle import CandyBundle
from core.candy.reward_policy import RewardPolicy
from core.capture.application.capture_unit_of_work import CaptureUnitOfWork
from core.creature.creature_factory import CreatureFactory
from core.safari.activity_repository import SafariActivityRepository
from core.safari.capture import (
    SafariPersistedCapture,
    SafariPersistedEncounterResult,
    SafariPersistedSlotResult,
)
from core.safari.capture_resolution import (
    SafariCaptureResolver,
    SafariEncounterResolution,
    SafariSlotOutcome,
)
from core.safari.domain import (
    SAFARI_ZONE_DEFINITION_BY_ZONE,
    SafariComposition,
    SafariEncounterStatus,
    SafariSessionStatus,
    SafariSlotStatus,
)
from core.safari.encounter import SafariEncounter, SafariEncounterSlot
from core.safari.encounter_context import SafariEncounterContext
from core.safari.encounter_generator import SafariEncounterGenerator
from core.safari.generated_encounter import SafariGeneratedEncounter
from core.safari.history import (
    SafariCapturedCreatureSnapshot,
    SafariEncounterHistoryEntry,
)
from core.safari.participant import NotEnoughSafariBalls, SafariParticipant
from core.safari.session import SafariSession

logger = logging.getLogger(__name__)


class SafariCaptureApplicationService:
    def __init__(
        self,
        activity_repository: SafariActivityRepository,
        capture_resolver: SafariCaptureResolver,
        unit_of_work: CaptureUnitOfWork,
        reward_policy: RewardPolicy,
        creature_factory: type[CreatureFactory] = CreatureFactory,
        encounter_generator: SafariEncounterGenerator | None = None,
        random_source: object | None = None,
    ) -> None:
        self._activity_repository = activity_repository
        self._capture_resolver = capture_resolver
        self._unit_of_work = unit_of_work
        self._reward_policy = reward_policy
        self._creature_factory = creature_factory
        self._encounter_generator = encounter_generator
        self._random_source = random_source

    async def select_capture(
        self,
        guild_id: int,
        trainer_id: int,
        slot_id: UUID,
        ball_count: int,
    ) -> SelectSafariCaptureResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            encounter = self._require_open_encounter(session)
            participant = self._participant(session, trainer_id)
            slot = self._slot(encounter, slot_id)
            self._validate_ball_count(participant, ball_count)

            session.select_capture(trainer_id, slot_id, ball_count)
            await self._activity_repository.save_session(session)
            logger.debug(
                "safari_selection_opened guild_id=%s trainer_id=%s slot_id=%s "
                "balls=%s remaining_balls=%s",
                guild_id,
                trainer_id,
                slot_id,
                ball_count,
                participant.remaining_balls,
            )

            return SelectSafariCaptureResult(
                session=session,
                encounter=encounter,
                participant=participant,
                slot=slot,
                balls_selected=ball_count,
                balls_available=participant.remaining_balls,
                selection=encounter.selection_for(trainer_id),
                state=SafariCaptureSelectionState.PENDING,
            )

    async def decline_capture(
        self,
        guild_id: int,
        trainer_id: int,
    ) -> DeclineSafariCaptureResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            encounter = self._require_open_encounter(session)
            participant = self._participant(session, trainer_id)
            selection = encounter.selection_for(trainer_id)

            session.decline_capture(trainer_id)
            await self._activity_repository.save_session(session)
            logger.debug(
                "safari_selection_declined guild_id=%s trainer_id=%s "
                "slot_id=%s remaining_balls=%s",
                guild_id,
                trainer_id,
                selection.slot_id if selection is not None else None,
                participant.remaining_balls,
            )

            return DeclineSafariCaptureResult(
                session=session,
                encounter=encounter,
                participant=participant,
                selection=selection,
                balls_available=participant.remaining_balls,
                state=SafariCaptureSelectionState.DECLINED,
            )

    async def confirm_capture_selection(
        self,
        guild_id: int,
        trainer_id: int,
    ) -> ConfirmSafariCaptureSelectionResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            encounter = self._require_open_encounter(session)
            participant = self._participant(session, trainer_id)
            selection = encounter.selection_for(trainer_id)

            if selection is None:
                raise SafariCaptureSelectionNotFound(
                    "Safari capture selection was not found."
                )

            session.confirm_selection(trainer_id)
            await self._activity_repository.save_session(session)

            confirmed = encounter.selection_for(trainer_id)
            assert confirmed is not None
            logger.debug(
                "safari_selection_confirmed guild_id=%s trainer_id=%s slot_id=%s "
                "balls_spent=%s remaining_balls=%s",
                guild_id,
                trainer_id,
                confirmed.slot_id,
                confirmed.ball_count,
                participant.remaining_balls,
            )

            return ConfirmSafariCaptureSelectionResult(
                session=session,
                encounter=encounter,
                participant=participant,
                selection=confirmed,
                balls_spent=confirmed.ball_count,
                balls_available=participant.remaining_balls,
                state=SafariCaptureSelectionState.CONFIRMED,
            )

    async def close_capture_selection(
        self,
        guild_id: int,
    ) -> CloseSafariCaptureSelectionResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            encounter = self._require_active_encounter(session)

            if encounter.status is SafariEncounterStatus.RESOLVING:
                return self._close_result(session, encounter)
            if session.status is not SafariSessionStatus.ENCOUNTER:
                raise SafariCaptureSelectionUnavailable(
                    "Safari capture selection cannot be closed."
                )

            confirmed_ids = {
                trainer_id
                for trainer_id, selection in encounter.selections_by_trainer.items()
                if selection.is_confirmed
            }
            for trainer_id in sorted(encounter.eligible_participant_ids):
                if trainer_id not in confirmed_ids:
                    session.decline_capture(trainer_id)

            await self._activity_repository.save_session(session)
            logger.debug(
                "safari_selection_closed guild_id=%s session_id=%s confirmed=%s "
                "declined=%s status=%s",
                guild_id,
                session.id,
                len(confirmed_ids),
                len(encounter.declined_participant_ids),
                encounter.status.value,
            )
            return self._close_result(session, encounter)

    async def resolve_capture(
        self,
        guild_id: int,
    ) -> ResolveSafariCaptureResult:
        async with self._activity_repository.lock(guild_id):
            session = await self._require_session(guild_id)
            encounter = self._require_resolving_encounter(session)
            next_encounter = await self._next_encounter_if_needed(session)

            resolution = self._capture_resolver.resolve(encounter)
            slot_application_results, persisted_result, rewards_by_trainer = (
                await self._persist_resolution(resolution)
            )
            history_entry = self._build_history_entry(
                encounter,
                resolution,
                slot_application_results,
            )
            try:
                session.apply_persisted_encounter_result(
                    persisted_result,
                    history_entry=history_entry,
                )
                if (
                    next_encounter is not None
                    and session.status is SafariSessionStatus.ENCOUNTER
                ):
                    session.publish_encounter(next_encounter.encounter)
                await self._activity_repository.save_session(session)
            except Exception:
                logger.exception(
                    "failed to apply safari encounter result guild_id=%s "
                    "session_id=%s encounter_id=%s",
                    guild_id,
                    session.id,
                    encounter.id,
                )
                raise

            logger.info(
                "safari_encounter_resolved guild_id=%s session_id=%s encounter_id=%s "
                "captured=%s escaped=%s next_status=%s",
                guild_id,
                session.id,
                encounter.id,
                sum(1 for result in slot_application_results if result.creature),
                sum(1 for result in slot_application_results if not result.creature),
                session.status.value,
            )

            return ResolveSafariCaptureResult(
                session=session,
                encounter_resolution=resolution,
                persisted_result=persisted_result,
                slot_results=slot_application_results,
                rewards_by_trainer=rewards_by_trainer,
                balls_committed_by_trainer=resolution.balls_committed_by_trainer,
                next_session_status=session.status,
            )

    async def _persist_resolution(
        self,
        resolution: SafariEncounterResolution,
    ) -> tuple[
        tuple[SafariCaptureSlotApplicationResult, ...],
        SafariPersistedEncounterResult,
        Mapping[int, CandyBundle],
    ]:
        captured_outcomes = [
            outcome
            for outcome in resolution.slot_outcomes
            if outcome.status is SafariSlotStatus.CAPTURED
        ]
        if not captured_outcomes:
            slot_results = tuple(
                SafariCaptureSlotApplicationResult(
                    slot_outcome=outcome,
                    creature=None,
                    persisted_capture=None,
                    reward=CandyBundle(),
                    collection_number=None,
                )
                for outcome in resolution.slot_outcomes
            )
            persisted = SafariPersistedEncounterResult(
                resolution.encounter_id,
                tuple(
                    SafariPersistedSlotResult(
                        outcome.slot_id,
                        outcome.status,
                    )
                    for outcome in resolution.slot_outcomes
                ),
            )
            return slot_results, persisted, {}

        captured_by_trainer: dict[int, list[SafariSlotOutcome]] = defaultdict(list)
        for outcome in captured_outcomes:
            assert outcome.winner_trainer_id is not None
            captured_by_trainer[outcome.winner_trainer_id].append(outcome)

        slot_results_by_slot: dict[UUID, SafariCaptureSlotApplicationResult] = {}
        rewards_by_trainer: dict[int, CandyBundle] = {}
        persisted_captures_by_slot: dict[UUID, SafariPersistedCapture] = {}

        async with self._unit_of_work.transaction() as transaction:
            for trainer_id in sorted(captured_by_trainer):
                trainer_reward = CandyBundle()
                trainer_outcomes = captured_by_trainer[trainer_id]

                for outcome in trainer_outcomes:
                    creature = self._creature_factory.create(
                        trainer_id=trainer_id,
                        opportunity=outcome.final_opportunity,
                    )
                    saved_creature = await transaction.save_creature(creature)
                    reward = self._reward_policy.reward_for(saved_creature)
                    trainer_reward = trainer_reward.merge(reward)
                    persisted_capture = SafariPersistedCapture(
                        trainer_id=trainer_id,
                        slot_id=outcome.slot_id,
                        creature_id=saved_creature.id,
                    )
                    persisted_captures_by_slot[outcome.slot_id] = persisted_capture

                    slot_results_by_slot[outcome.slot_id] = (
                        SafariCaptureSlotApplicationResult(
                            slot_outcome=outcome,
                            creature=saved_creature,
                            persisted_capture=persisted_capture,
                            reward=reward,
                            collection_number=saved_creature.collection_number,
                        )
                    )

                inventory = await transaction.get_candy_inventory(trainer_id)
                inventory.add(trainer_reward)
                await transaction.save_candy_inventory(trainer_id, inventory)
                rewards_by_trainer[trainer_id] = trainer_reward

        ordered_slot_results: list[SafariCaptureSlotApplicationResult] = []
        for outcome in resolution.slot_outcomes:
            if outcome.status is SafariSlotStatus.CAPTURED:
                ordered_slot_results.append(slot_results_by_slot[outcome.slot_id])
            else:
                ordered_slot_results.append(
                    SafariCaptureSlotApplicationResult(
                        slot_outcome=outcome,
                        creature=None,
                        persisted_capture=None,
                        reward=CandyBundle(),
                        collection_number=None,
                    )
                )

        persisted_result = SafariPersistedEncounterResult(
            resolution.encounter_id,
            tuple(
                SafariPersistedSlotResult(
                    outcome.slot_id,
                    outcome.status,
                    persisted_captures_by_slot.get(outcome.slot_id),
                )
                for outcome in resolution.slot_outcomes
            ),
        )

        return (
            tuple(ordered_slot_results),
            persisted_result,
            MappingProxyType(rewards_by_trainer),
        )

    @staticmethod
    def _build_history_entry(
        encounter: SafariEncounter,
        resolution: SafariEncounterResolution,
        slot_application_results: tuple[SafariCaptureSlotApplicationResult, ...],
    ) -> SafariEncounterHistoryEntry:
        captured_creatures = tuple(
            SafariCapturedCreatureSnapshot(
                slot_id=result.slot_outcome.slot_id,
                trainer_id=result.creature.trainer_id,
                creature_id=result.creature.id,
                creature=result.creature,
            )
            for result in slot_application_results
            if result.creature is not None
        )
        return SafariEncounterHistoryEntry(
            encounter=encounter,
            resolution=resolution,
            captured_creatures=captured_creatures,
            eligible_participant_ids=encounter.eligible_participant_ids,
        )

    async def _next_encounter_if_needed(
        self,
        session: SafariSession,
    ) -> SafariGeneratedEncounter | None:
        if self._encounter_generator is None or self._random_source is None:
            return None
        if session.current_segment.remaining_encounters <= 1:
            return None
        if not any(
            participant.can_capture
            for participant in session.participants_by_trainer.values()
        ):
            return None
        return await self._generate_next_encounter(session)

    async def _generate_next_encounter(
        self,
        session: SafariSession,
    ) -> SafariGeneratedEncounter:
        assert self._encounter_generator is not None
        assert self._random_source is not None

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
        compositions = self._encounter_compositions_for(session)
        return await self._encounter_generator.generate_with_events(
            context,
            compositions,
        )

    @staticmethod
    def _encounter_compositions_for(
        session: SafariSession,
    ) -> tuple[SafariComposition, ...]:
        if (
            session.completed_encounter_count + 2 == session.total_encounters
            and not session.has_special_encounter_history
        ):
            return (
                SafariComposition.SOLITARY,
                SafariComposition.NORMAL,
            )
        return (SafariComposition.NORMAL,)

    async def _require_session(self, guild_id: int) -> SafariSession:
        session = await self._activity_repository.get_session(guild_id)
        if session is None:
            raise SafariSessionNotFound("Safari session was not found.")
        return session

    @staticmethod
    def _require_active_encounter(session: SafariSession) -> SafariEncounter:
        encounter = session.current_encounter
        if encounter is None:
            raise SafariCaptureSelectionUnavailable(
                "Safari capture encounter is not available."
            )
        return encounter

    def _require_open_encounter(self, session: SafariSession) -> SafariEncounter:
        if session.status is not SafariSessionStatus.ENCOUNTER:
            raise SafariCaptureSelectionUnavailable(
                "Safari capture selection is not available."
            )
        encounter = self._require_active_encounter(session)
        if encounter.status is not SafariEncounterStatus.OPEN:
            raise SafariCaptureSelectionUnavailable(
                "Safari capture selection is not available."
            )
        return encounter

    def _require_resolving_encounter(self, session: SafariSession) -> SafariEncounter:
        if session.status is not SafariSessionStatus.RESOLUTION:
            raise SafariCaptureResolutionUnavailable(
                "Safari capture resolution is not available."
            )
        encounter = self._require_active_encounter(session)
        if encounter.status is not SafariEncounterStatus.RESOLVING:
            raise SafariCaptureResolutionUnavailable(
                "Safari capture resolution is not available."
            )
        return encounter

    def _participant(
        self,
        session: SafariSession,
        trainer_id: int,
    ) -> SafariParticipant:
        participant = session.participants_by_trainer.get(trainer_id)
        if participant is None:
            raise SafariCaptureSelectionUnavailable(
                "trainer is not a Safari participant."
            )
        return participant

    @staticmethod
    def _slot(
        encounter: SafariEncounter,
        slot_id: UUID,
    ) -> SafariEncounterSlot:
        for slot in encounter.slots:
            if slot.id == slot_id:
                return slot
        raise SafariCaptureSelectionUnavailable("Safari encounter slot was not found.")

    @staticmethod
    def _validate_ball_count(
        participant: SafariParticipant,
        ball_count: int,
    ) -> None:
        if ball_count < 1 or ball_count > 3:
            raise ValueError("ball_count must be between 1 and 3.")
        if ball_count > participant.remaining_balls:
            raise NotEnoughSafariBalls("Not enough Safari Balls remaining.")

    @staticmethod
    def _close_result(
        session: SafariSession,
        encounter: SafariEncounter,
    ) -> CloseSafariCaptureSelectionResult:
        confirmed_ids = tuple(
            sorted(
                trainer_id
                for trainer_id, selection in encounter.selections_by_trainer.items()
                if selection.is_confirmed
            )
        )
        declined_ids = tuple(sorted(encounter.declined_participant_ids))
        return CloseSafariCaptureSelectionResult(
            session=session,
            encounter=encounter,
            confirmed_participant_ids=confirmed_ids,
            declined_participant_ids=declined_ids,
            state=encounter.status,
        )
