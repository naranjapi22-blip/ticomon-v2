from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from uuid import UUID, uuid4

from application.pvp.events import PvpEventTranslator
from application.pvp.models import PvpAction, PvpLegalActions, is_decisive_event
from application.pvp.snapshots import PvpBattleSnapshot, snapshot_battle
from application.pvp.task_management import cancel_tasks_safely, register_task
from application.pvp.team_validator import PvpTeamValidator
from core.pvp.session import (
    ACTION_TIMEOUT_SECONDS,
    FORCED_SWITCH_TIMEOUT_SECONDS,
    MAX_PVP_DURATION_SECONDS,
    MAX_PVP_TURNS,
    PvpPhase,
    PvpSession,
    PvpSessionRegistry,
)
from infrastructure.battle.poke_env.pvp_controller import (
    PokeEnvPvpController,
    PvpControllerCallbacks,
)

logger = logging.getLogger(__name__)


def _event_matches_pokemon(event_name: str | None, pokemon) -> bool:
    if not event_name or pokemon is None:
        return False

    def normalize(value) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value).casefold())

    return normalize(event_name) == normalize(pokemon.species_name)


def _faint_snapshot_pokemon(pokemon):
    if pokemon is None:
        return None
    return replace(pokemon, current_hp=0, hp_fraction=0.0, status="FNT", fainted=True)


def _apply_terminal_event(snapshot: PvpBattleSnapshot) -> PvpBattleSnapshot:
    event = snapshot.last_decisive_event
    if event is None or not event.fainted:
        return snapshot

    player_active = snapshot.player_active
    opponent_active = snapshot.opponent_active
    player_team = snapshot.player_team
    opponent_team = snapshot.opponent_team
    if _event_matches_pokemon(event.target, player_active):
        player_active = _faint_snapshot_pokemon(player_active)
    if _event_matches_pokemon(event.target, opponent_active):
        opponent_active = _faint_snapshot_pokemon(opponent_active)
    player_team = tuple(
        (
            _faint_snapshot_pokemon(pokemon)
            if _event_matches_pokemon(event.target, pokemon)
            else pokemon
        )
        for pokemon in player_team
    )
    opponent_team = tuple(
        (
            _faint_snapshot_pokemon(pokemon)
            if _event_matches_pokemon(event.target, pokemon)
            else pokemon
        )
        for pokemon in opponent_team
    )
    player_targeted = _event_matches_pokemon(event.target, snapshot.player_active)
    opponent_targeted = _event_matches_pokemon(event.target, snapshot.opponent_active)
    player_remaining = (
        sum(not pokemon.fainted for pokemon in player_team)
        if player_team
        else max(0, snapshot.player_remaining - int(player_targeted))
    )
    opponent_remaining = (
        sum(not pokemon.fainted for pokemon in opponent_team)
        if opponent_team
        else max(0, snapshot.opponent_remaining - int(opponent_targeted))
    )
    return replace(
        snapshot,
        player_active=player_active,
        opponent_active=opponent_active,
        player_remaining=player_remaining,
        opponent_remaining=opponent_remaining,
        player_team=player_team,
        opponent_team=opponent_team,
    )


def _safe_exception_message(error: BaseException) -> str:
    message = str(error).replace("\r", " ").replace("\n", " ").strip()
    for secret_name in (
        "DISCORD_TOKEN",
        "NEON_DATABASE_URL",
        "SHOWDOWN_WEBSOCKET_URL",
        "SHOWDOWN_AUTHENTICATION_URL",
    ):
        secret = os.getenv(secret_name)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    message = re.sub(
        r"(?i)(authorization|password|secret|token)(\s*[:=]\s*)\S+",
        r"\1\2[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)(https?://)([^/\s:@]+):([^@\s]+)@",
        r"\1[REDACTED]@",
        message,
    )
    return message[:500] or "<no exception message>"


class PvpApplicationService:
    """Coordinates PvP lifecycle without sharing state with legacy battles."""

    def __init__(
        self,
        registry: PvpSessionRegistry | None = None,
        creature_repository=None,
        controller_factory: Callable[[], object] | None = None,
        team_validator: PvpTeamValidator | None = None,
        team_repository=None,
        random_source: random.Random | None = None,
    ) -> None:
        self.registry = registry or PvpSessionRegistry()
        self._creature_repository = creature_repository
        self._controller_factory = controller_factory or PokeEnvPvpController
        self._team_validator = team_validator or PvpTeamValidator()
        self._team_repository = team_repository
        self._random = random_source or random.Random()
        self._action_waiters: dict[tuple[UUID, int], asyncio.Future[PvpAction]] = {}
        self._legal_actions: dict[tuple[UUID, int], PvpLegalActions] = {}
        self._request_ids: dict[tuple[UUID, int], str] = {}
        self._event_handlers: dict[UUID, Callable[[str], Awaitable[None]]] = {}
        self._finish_handlers: dict[UUID, Callable[[object], Awaitable[None]]] = {}
        self._snapshot_handlers: dict[
            UUID, Callable[[PvpBattleSnapshot], Awaitable[None]]
        ] = {}
        self._action_handlers: dict[
            UUID, Callable[[int, PvpLegalActions], Awaitable[None]]
        ] = {}
        self._cleanup_handlers: dict[UUID, Callable[[UUID], Awaitable[None]]] = {}
        self._finished_sessions: set[UUID] = set()
        self._finalizing_sessions: set[UUID] = set()
        self._event_translators: dict[UUID, PvpEventTranslator] = {}
        self._latest_snapshots: dict[UUID, dict[int, PvpBattleSnapshot]] = {}
        self._protocol_event_keys: dict[UUID, set[tuple]] = {}
        self._last_decisive_events: dict[UUID, tuple[object, int]] = {}
        self._cleaned_sessions: dict[UUID, PvpSession] = {}
        self._cleanup_tasks: dict[UUID, asyncio.Task] = {}

    def challenge(self, initiator_id: int, opponent_id: int) -> PvpSession:
        return self.registry.create(initiator_id, opponent_id)

    def is_cleaned_up(self, session_id: UUID) -> bool:
        return session_id in self._cleaned_sessions

    async def get_team_selector(self, trainer_id: int) -> list[tuple[int, str]]:
        if self._creature_repository is None:
            raise RuntimeError("PvP creature repository is not configured.")
        if self._team_repository is None:
            raise RuntimeError("PvP team repository is not configured.")
        team_slots = await self._team_repository.get_by_trainer(trainer_id)
        creatures = await self._creature_repository.get_many(
            [slot.creature_id for slot in team_slots]
        )
        creatures_by_id = {creature.id: creature for creature in creatures}
        options = []
        for slot in team_slots:
            creature = creatures_by_id.get(slot.creature_id)
            if creature is None:
                continue
            try:
                self._team_validator.validate_creature(creature)
            except ValueError:
                continue
            if creature.collection_number is None:
                continue
            label = creature.species.name.title()
            if creature.is_shiny:
                label = f"✨ {label}"
            options.append(
                (creature.collection_number, f"#{creature.collection_number} {label}")
            )
        return options

    async def select_team(
        self,
        session_id: UUID,
        trainer_id: int,
        collection_numbers: list[int] | tuple[int, ...],
    ) -> tuple:
        session = self.registry.get(session_id)
        if self._creature_repository is None:
            raise RuntimeError("PvP creature repository is not configured.")
        if self._team_repository is None:
            raise RuntimeError("PvP team repository is not configured.")
        team_slots = await self._team_repository.get_by_trainer(trainer_id)
        configured_ids = {slot.creature_id for slot in team_slots}
        creatures = []
        for collection_number in collection_numbers:
            creature = await self._creature_repository.get_by_collection_number(
                trainer_id, collection_number
            )
            if creature.trainer_id != trainer_id:
                raise ValueError("You can only select your own creatures.")
            if creature.id not in configured_ids:
                raise ValueError("Every selected creature must belong to your team.")
            creatures.append(creature)
        team = self._team_validator.validate(creatures)
        async with session.lock:
            session.select_team(trainer_id, tuple(creature.id for creature in team))
            session.selected_creatures[trainer_id] = team
        return team

    async def confirm_team(
        self,
        session_id: UUID,
        trainer_id: int,
        *,
        on_event: Callable[[str], Awaitable[None]] | None = None,
        on_finished: Callable[[object], Awaitable[None]] | None = None,
        on_snapshot: Callable[[PvpBattleSnapshot], Awaitable[None]] | None = None,
        on_actions: Callable[[int, PvpLegalActions], Awaitable[None]] | None = None,
        on_cleanup: Callable[[UUID], Awaitable[None]] | None = None,
        start_gate: Callable[[UUID], Awaitable[None]] | None = None,
    ) -> bool:
        session = self.registry.get(session_id)
        async with session.lock:
            if session.startup_claimed:
                return False
            ready = session.confirm_team(trainer_id)
            if not ready:
                return False
            selected = getattr(session, "selected_creatures", {})
            teams = {player_id: selected[player_id] for player_id in session.player_ids}
            if self._team_repository is None:
                raise RuntimeError("PvP team repository is not configured.")
            for player_id, team in teams.items():
                slots = await self._team_repository.get_by_trainer(player_id)
                configured_ids = {slot.creature_id for slot in slots}
                if any(creature.id not in configured_ids for creature in team):
                    raise ValueError(
                        "A selected creature is no longer in the trainer's team."
                    )
                refreshed = await self._creature_repository.get_many(
                    [creature.id for creature in team]
                )
                original_ids = [creature.id for creature in team]
                refreshed_by_id = {creature.id: creature for creature in refreshed}
                if (
                    len(original_ids) != len(set(original_ids))
                    or len(refreshed_by_id) != len(refreshed)
                    or len(refreshed) != len(team)
                    or set(refreshed_by_id) != set(original_ids)
                    or any(creature.trainer_id != player_id for creature in refreshed)
                ):
                    raise ValueError("A selected creature is no longer owned by you.")
                ordered_refreshed = tuple(
                    refreshed_by_id[creature_id] for creature_id in original_ids
                )
                self._team_validator.validate(ordered_refreshed)
                session.selected_creatures[player_id] = ordered_refreshed
            teams = {
                player_id: session.selected_creatures[player_id]
                for player_id in session.player_ids
            }
            all_creatures = tuple(
                creature for team in teams.values() for creature in team
            )
            if len({creature.species.id for creature in all_creatures}) != 6:
                raise ValueError("A PvP battle cannot contain duplicate species.")
            self._team_validator.validate(teams[session.initiator_id])
            self._team_validator.validate(teams[session.opponent_id])
            self.registry.reserve_creatures(
                session_id,
                tuple(creature.id for creature in all_creatures),
            )
            session.phase = PvpPhase.STARTING
            session.startup_claimed = True
            if start_gate is not None:
                try:
                    await start_gate(session_id)
                except Exception:
                    session.startup_claimed = False
                    session.phase = PvpPhase.WAITING_FOR_ACTIONS
                    await self.cleanup(session_id)
                    raise
            try:
                controller = self._controller_factory()
            except Exception:
                session.startup_claimed = False
                session.cancel()
                self.registry.remove(session_id)
                raise
            session.battle_controller = controller
            self._event_translators[session_id] = PvpEventTranslator(
                session.initiator_id, session.opponent_id
            )
            if on_event is not None:
                self._event_handlers[session_id] = on_event
            if on_finished is not None:
                self._finish_handlers[session_id] = on_finished
            if on_snapshot is not None:
                self._snapshot_handlers[session_id] = on_snapshot
            if on_actions is not None:
                self._action_handlers[session_id] = on_actions
            if on_cleanup is not None:
                self._cleanup_handlers[session_id] = on_cleanup
            session.begin_battle()
            session.phase = PvpPhase.STARTING

        callbacks = PvpControllerCallbacks(
            on_actions=lambda player_id, legal: self.request_action(
                session_id, player_id, legal
            ),
            on_protocol=lambda source_player_id, messages: self.handle_protocol(
                session_id, messages, source_player_id=source_player_id
            ),
            on_finished=lambda battle: self.finish_from_controller(session_id, battle),
            on_snapshot=lambda snapshot: self.handle_snapshot(session_id, snapshot),
            on_error=lambda error: self.handle_controller_error(session_id, error),
        )
        task = register_task(
            asyncio.create_task(
                self._start_controller(
                    session_id, session, controller, teams, callbacks
                ),
                name=f"pvp-startup:{session_id}",
            ),
            owner="PvpApplicationService",
            role="startup",
        )
        session.startup_task = task
        session.timeout_tasks.add(task)
        task.add_done_callback(self._consume_start_task)
        return True

    async def _start_controller(
        self, session_id, session, controller, teams, callbacks
    ) -> None:
        try:
            await controller.start(teams, callbacks)
            session.phase = PvpPhase.WAITING_FOR_ACTIONS
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning(
                "PvP startup failed session_id=%s phase=%s error_type=%s error=%s",
                session_id,
                session.phase.value,
                type(error).__name__,
                _safe_exception_message(error),
                exc_info=True,
            )
            handler = self._event_handlers.get(session_id)
            try:
                if handler is not None:
                    await handler("PvP could not start. The challenge was cancelled.")
            except Exception:
                logger.debug("Unable to publish PvP startup failure", exc_info=True)
            await self.cleanup(session_id)

    async def handle_controller_error(
        self, session_id: UUID, error: BaseException
    ) -> None:
        logger.warning(
            "PvP controller task failed session_id=%s phase=%s error_type=%s error=%s",
            session_id,
            self._session_phase(session_id),
            type(error).__name__,
            _safe_exception_message(error),
            exc_info=(type(error), error, error.__traceback__),
        )
        handler = self._event_handlers.get(session_id)
        if handler is not None:
            try:
                await handler("PvP ended unexpectedly and was cleaned up.")
            except Exception:
                logger.debug("Unable to publish PvP controller failure", exc_info=True)
        await self.finish_from_controller(session_id, None, reason="error")

    def _session_phase(self, session_id: UUID) -> str:
        try:
            return self.registry.get(session_id).phase.value
        except ValueError:
            return "unknown"

    @staticmethod
    def _consume_start_task(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        try:
            task.exception()
        except Exception:
            logger.debug("Unable to retrieve PvP startup task exception", exc_info=True)

    async def request_action(
        self,
        session_id: UUID,
        trainer_id: int,
        legal: PvpLegalActions,
    ) -> PvpAction:
        session = self.registry.get(session_id)
        async with session.lock:
            if session.phase is PvpPhase.RESOLVING:
                session.next_turn()
            if session.turn_number > MAX_PVP_TURNS or (
                session.started_monotonic is not None
                and time.monotonic() - session.started_monotonic
                > MAX_PVP_DURATION_SECONDS
            ):
                session.cancel()
                raise ValueError("The PvP technical battle limit was reached.")
            if session.phase not in {
                PvpPhase.WAITING_FOR_ACTIONS,
                PvpPhase.FORCED_SWITCH,
            }:
                raise ValueError("PvP is not accepting actions.")
            session.phase = (
                PvpPhase.FORCED_SWITCH
                if legal.forced_switch
                else PvpPhase.WAITING_FOR_ACTIONS
            )
            key = (session_id, trainer_id)
            loop = asyncio.get_running_loop()
            future: asyncio.Future[PvpAction] = loop.create_future()
            request_id = str(uuid4())
            self._action_waiters[key] = future
            self._legal_actions[key] = legal
            translator = self._event_translators.get(session_id)
            if translator is not None:
                translator.set_move_categories(legal)
            self._request_ids[key] = request_id
            session.register_action_request(trainer_id, request_id)
            timeout = (
                FORCED_SWITCH_TIMEOUT_SECONDS
                if legal.forced_switch
                else ACTION_TIMEOUT_SECONDS
            )
            action_handler = self._action_handlers.get(session_id)
        if action_handler is not None:
            await action_handler(trainer_id, legal)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
        except asyncio.TimeoutError:
            action = self._automatic_action(legal)
            if legal.forced_switch:
                logger.warning(
                    "PvP forced switch timed out; applying automatic selection "
                    "session_id=%s trainer_id=%s policy=automatic_selection",
                    session_id,
                    trainer_id,
                )
            async with session.lock:
                request_id = self._request_ids.get(key)
                applied = request_id is not None and session.try_choose_action(
                    trainer_id, request_id, action.identifier
                )
                if applied:
                    if not future.done():
                        future.set_result(action)
                    self._begin_resolution_if_ready(session, session_id)
                    logger.info(
                        "Applied PvP action timeout",
                        extra=self._log_context(
                            session, trainer_id, request_id, legal, "applied"
                        ),
                    )
                    return action
                logger.info(
                    "Discarded obsolete PvP action timeout",
                    extra=self._log_context(
                        session, trainer_id, request_id, legal, "discarded"
                    ),
                )
                if future.done() and not future.cancelled():
                    return future.result()
                raise asyncio.CancelledError
        finally:
            if self._action_waiters.get(key) is future:
                self._action_waiters.pop(key, None)
                self._legal_actions.pop(key, None)
                self._request_ids.pop(key, None)

    async def submit_action(
        self,
        session_id: UUID,
        trainer_id: int,
        action: PvpAction,
    ) -> bool:
        session = self.registry.get(session_id)
        if (
            session_id in self._finalizing_sessions
            or session_id in self._finished_sessions
        ):
            return False
        async with session.lock:
            key = (session_id, trainer_id)
            legal = self._legal_actions.get(key)
            future = self._action_waiters.get(key)
            request_id = self._request_ids.get(key)
            if legal is None or future is None or request_id is None or future.done():
                return False
            if action.identifier not in {item.identifier for item in legal.all_actions}:
                raise ValueError("That action is not legal in the current state.")
            if not session.try_choose_action(trainer_id, request_id, action.identifier):
                return False
            future.set_result(action)
            self._begin_resolution_if_ready(session, session_id)
            return True

    def _begin_resolution_if_ready(self, session: PvpSession, session_id: UUID) -> None:
        pending = [
            future
            for (pending_session_id, _), future in self._action_waiters.items()
            if pending_session_id == session_id
        ]
        if len(pending) == 2 and all(future.done() for future in pending):
            session.begin_resolution()

    @staticmethod
    def _log_context(session, trainer_id, request_id, legal, timeout_status):
        return {
            "session_id": str(session.id),
            "trainer_id": trainer_id,
            "request_id": request_id,
            "request_type": "forced_switch" if legal.forced_switch else "move",
            "session_state": session.phase.value,
            "timeout_status": timeout_status,
        }

    def legal_actions_for(self, session_id: UUID, trainer_id: int) -> PvpLegalActions:
        self.registry.get(session_id)._require_player(trainer_id)
        try:
            return self._legal_actions[(session_id, trainer_id)]
        except KeyError as error:
            raise ValueError(
                "Showdown is not currently waiting for your action."
            ) from error

    async def forfeit(self, session_id: UUID, trainer_id: int) -> None:
        session = self.registry.get(session_id)
        session._require_player(trainer_id)
        controller = session.battle_controller
        if controller is not None:
            await controller.forfeit(trainer_id)
        winner_id = next(
            player_id for player_id in session.player_ids if player_id != trainer_id
        )
        await self.finish_from_controller(
            session_id,
            None,
            winner_id=winner_id,
            winner_name=None,
            reason="forfeit",
        )

    async def handle_protocol(
        self,
        session_id: UUID,
        messages: list[list[str]],
        *,
        source_player_id: int | None = None,
    ) -> None:
        if (
            session_id in self._finalizing_sessions
            or session_id in self._finished_sessions
            or session_id in self._cleaned_sessions
        ):
            logger.info(
                "Ignoring PvP protocol after finalization session_id=%s",
                session_id,
            )
            return
        session = self.registry.get(session_id)
        canonical_source = session.initiator_id
        filtered_messages: list[list[str]] = []
        event_keys = self._protocol_event_keys.setdefault(session_id, set())
        for message in messages:
            if len(message) < 2:
                continue
            if (
                source_player_id is not None
                and source_player_id != canonical_source
                and message[1] not in {"win", "tie"}
            ):
                logger.debug(
                    "Ignoring non-canonical PvP protocol event session_id=%s "
                    "turn=%s canonical_source_player_id=%s "
                    "incoming_source_player_id=%s ignored_reason=non_canonical_source",
                    session_id,
                    session.turn_number,
                    canonical_source,
                    source_player_id,
                )
                continue
            event_key = (
                session.turn_number,
                message[1],
                tuple(str(value).strip() for value in message[2:]),
            )
            if event_key in event_keys:
                logger.debug(
                    "Ignoring duplicate PvP protocol event session_id=%s turn=%s "
                    "canonical_source_player_id=%s incoming_source_player_id=%s "
                    "event_key=%s duplicate=true ignored_reason=duplicate_event",
                    session_id,
                    session.turn_number,
                    canonical_source,
                    source_player_id,
                    event_key,
                )
                continue
            event_keys.add(event_key)
            filtered_messages.append(message)
        messages = filtered_messages
        terminal_messages = [
            message for message in messages if message[1] in {"win", "tie"}
        ]
        if terminal_messages:
            narration_messages = [
                message for message in messages if message[1] not in {"win", "tie"}
            ]
            if narration_messages and source_player_id in {
                None,
                canonical_source,
            }:
                translator = self._event_translators.setdefault(
                    session_id,
                    PvpEventTranslator(),
                )
                steps = translator.translate(narration_messages)
                handler = self._event_handlers.get(session_id)
                for step in steps:
                    step = replace(step, turn=session.turn_number)
                    if is_decisive_event(step.event):
                        self._last_decisive_events[session_id] = (
                            step.event,
                            session.turn_number,
                        )
                    if handler is not None:
                        await handler(step)
            message = terminal_messages[0]
            winner_name = message[2] if len(message) > 2 else None
            winner_id = None
            resolver = getattr(session.battle_controller, "resolve_winner", None)
            if winner_name and resolver is not None:
                winner_id = resolver(winner_name)
            session.final_winner_name = winner_name
            session.final_winner_id = winner_id
            session.final_tie = message[1] == "tie"
            logger.info(
                "PvP terminal protocol received session_id=%s phase=%s turn=%s "
                "winner_name=%s winner_id=%s",
                session_id,
                session.phase.value,
                session.turn_number,
                winner_name,
                winner_id,
            )
            await self.finish_from_controller(
                session_id,
                None,
                winner_id=winner_id,
                winner_name=winner_name,
                tie=message[1] == "tie",
            )
            return
        if source_player_id is not None and source_player_id != canonical_source:
            logger.debug(
                "Ignoring non-canonical PvP narration source session_id=%s turn=%s "
                "canonical_source_player_id=%s incoming_source_player_id=%s "
                "ignored_reason=non_canonical_narration_source",
                session_id,
                session.turn_number,
                canonical_source,
                source_player_id,
            )
            return
        # Raw protocol is deliberately not rendered as history. The callback receives
        # only the current compact event and the board layer replaces the old one.
        translator = self._event_translators.setdefault(
            session_id,
            PvpEventTranslator(),
        )
        steps = translator.translate(messages)
        for step in steps:
            if is_decisive_event(step.event):
                self._last_decisive_events[session_id] = (
                    step.event,
                    session.turn_number,
                )
        diagnostic = translator.last_damage_diagnostic
        if diagnostic is not None:
            actor = next(
                (
                    str(message[2])[:80]
                    for message in messages
                    if len(message) >= 3 and message[1] == "move"
                ),
                None,
            )
            logger.debug(
                "PvP damage diagnostic session_id=%s turn=%s "
                "canonical_source_player_id=%s incoming_source_player_id=%s "
                "actor=%s target=%s previous_hp=%s resulting_hp=%s "
                "calculated_damage=%s event_key=%s duplicate=false "
                "ignored_reason=%s",
                session_id,
                session.turn_number,
                canonical_source,
                source_player_id,
                actor,
                diagnostic.get("target"),
                diagnostic.get("previous_hp"),
                diagnostic.get("resulting_hp"),
                diagnostic.get("calculated_damage"),
                (
                    session.turn_number,
                    "-damage",
                    diagnostic.get("target"),
                    diagnostic.get("resulting_hp"),
                ),
                None,
            )
        handler = self._event_handlers.get(session_id)
        if handler is not None:
            for step in steps:
                step = replace(step, turn=session.turn_number)
                await handler(step)

    async def finish_from_controller(
        self,
        session_id: UUID,
        battle: object | None,
        *,
        winner_id: int | None = None,
        winner_name: str | None = None,
        tie: bool = False,
        reason: str | None = None,
    ) -> None:
        if (
            session_id in self._finished_sessions
            or session_id in self._finalizing_sessions
            or session_id in self._cleaned_sessions
        ):
            return
        self._finished_sessions.add(session_id)
        self._finalizing_sessions.add(session_id)
        handler = self._finish_handlers.get(session_id)
        try:
            session = self.registry.get(session_id)
            session.phase = PvpPhase.FINALIZING
            session.final_winner_id = winner_id or session.final_winner_id
            session.final_winner_name = winner_name or session.final_winner_name
            session.final_tie = tie or session.final_tie
            session.final_reason = reason or session.final_reason
            last_event = self._last_decisive_events.get(session_id)
            try:
                final_snapshot = snapshot_battle(
                    battle,
                    player_id=session.initiator_id,
                    opponent_id=session.opponent_id,
                )
            except (AttributeError, TypeError, ValueError):
                final_snapshot = self._latest_snapshots.get(session_id, {}).get(
                    session.initiator_id
                )
            if final_snapshot is not None:
                if last_event is not None:
                    final_snapshot = replace(
                        final_snapshot,
                        last_decisive_event=last_event[0],
                        last_decisive_event_turn=last_event[1],
                    )
                final_snapshot = _apply_terminal_event(final_snapshot)
                logger.info(
                    "PvP final snapshot ready session_id=%s phase=%s turn=%s "
                    "source_player_id=%s winner_id=%s",
                    session_id,
                    session.phase.value,
                    final_snapshot.turn,
                    final_snapshot.player_id,
                    session.final_winner_id or final_snapshot.winner_id,
                )
                await self.handle_snapshot(session_id, final_snapshot, allow_final=True)
            if handler is not None:
                await handler(battle)
            session.finish()
            logger.info(
                "PvP final delivery completed session_id=%s phase=%s turn=%s "
                "winner_id=%s winner_name=%s",
                session_id,
                session.phase.value,
                session.turn_number,
                session.final_winner_id,
                session.final_winner_name,
            )
        except Exception as error:
            logger.error(
                "PvP final delivery failed session_id=%s phase=%s turn=%s "
                "winner_id=%s error_type=%s error=%s",
                session_id,
                self._session_phase(session_id),
                getattr(session, "turn_number", None),
                winner_id,
                type(error).__name__,
                _safe_exception_message(error),
                exc_info=True,
            )
        finally:
            await self.cleanup(session_id)

    async def handle_snapshot(
        self,
        session_id: UUID,
        snapshot: PvpBattleSnapshot,
        *,
        allow_final: bool = False,
    ) -> None:
        if session_id in self._finished_sessions and not allow_final:
            logger.info(
                "Ignoring stale PvP snapshot session_id=%s phase=finished "
                "incoming_turn=%s reason=stale_delivery_ignored",
                session_id,
                snapshot.turn,
            )
            return
        if session_id in self._finalizing_sessions and not allow_final:
            logger.info(
                "Ignoring stale PvP snapshot session_id=%s phase=finalizing "
                "incoming_turn=%s reason=stale_delivery_ignored",
                session_id,
                snapshot.turn,
            )
            return
        if session_id in self._cleaned_sessions:
            logger.info(
                "Ignoring PvP snapshot after cleanup session_id=%s "
                "incoming_turn=%s reason=cleaned_up",
                session_id,
                snapshot.turn,
            )
            return
        previous = self._latest_snapshots.setdefault(session_id, {}).get(
            snapshot.player_id
        )
        if previous is not None and snapshot.turn < previous.turn:
            logger.info(
                "Ignoring stale PvP snapshot session_id=%s phase=%s "
                "current_turn=%s incoming_turn=%s source_player=%s "
                "reason=stale_delivery_ignored",
                session_id,
                self._session_phase(session_id),
                previous.turn,
                snapshot.turn,
                snapshot.player_id,
            )
            return
        translator = self._event_translators.get(session_id)
        if translator is not None:
            session = self.registry.get(session_id)
            if snapshot.player_id == session.initiator_id:
                translator.observe_snapshot(snapshot)
        self._latest_snapshots[session_id][snapshot.player_id] = snapshot
        handler = self._snapshot_handlers.get(session_id)
        if handler is not None:
            await handler(snapshot)

    async def decline(self, session_id: UUID) -> None:
        session = self.registry.get(session_id)
        session.cancel()
        await self.cleanup(session_id)

    async def cleanup(self, session_id: UUID) -> None:
        if session_id in self._cleaned_sessions:
            return
        current_task = asyncio.current_task()
        existing_cleanup = self._cleanup_tasks.get(session_id)
        if existing_cleanup is not None:
            if existing_cleanup is current_task:
                logger.warning(
                    "Skipping self-await during PvP cleanup session_id=%s "
                    "task=%s reason=recursive_cleanup",
                    session_id,
                    current_task.get_name() if current_task is not None else None,
                )
                return
            logger.debug(
                "Waiting for existing PvP cleanup session_id=%s current_task=%s "
                "target_task=%s",
                session_id,
                current_task.get_name() if current_task is not None else None,
                existing_cleanup.get_name(),
            )
            await existing_cleanup
            return
        if current_task is not None:
            self._cleanup_tasks[session_id] = current_task
        try:
            session = self.registry.get(session_id)
        except ValueError:
            self._cleanup_tasks.pop(session_id, None)
            return
        try:
            for key, future in list(self._action_waiters.items()):
                if key[0] == session_id and not future.done():
                    future.cancel()
            self._action_waiters = {
                key: value
                for key, value in self._action_waiters.items()
                if key[0] != session_id
            }
            self._legal_actions = {
                key: value
                for key, value in self._legal_actions.items()
                if key[0] != session_id
            }
            self._request_ids = {
                key: value
                for key, value in self._request_ids.items()
                if key[0] != session_id
            }
            await cancel_tasks_safely(
                session.timeout_tasks,
                current_task=current_task,
                session_id=session_id,
                phase=session.phase,
                owner="PvpApplicationService",
                reason="session cleanup",
            )
            session.timeout_tasks.clear()
            session.startup_task = None
            session.startup_claimed = False
            controller = session.battle_controller
            if controller is not None:
                try:
                    await controller.close()
                except Exception:
                    logger.warning(
                        "PvP controller close failed during cleanup session_id=%s",
                        session_id,
                        exc_info=True,
                    )
            if session.phase is not PvpPhase.FINISHED:
                session.cancel()
            session.mark_cleaned_up()
            cleanup_handler = self._cleanup_handlers.get(session_id)
            if cleanup_handler is not None:
                await cleanup_handler(session_id)
            self._event_handlers.pop(session_id, None)
            self._finish_handlers.pop(session_id, None)
            self._snapshot_handlers.pop(session_id, None)
            self._action_handlers.pop(session_id, None)
            self._cleanup_handlers.pop(session_id, None)
            self._event_translators.pop(session_id, None)
            self._latest_snapshots.pop(session_id, None)
            self._protocol_event_keys.pop(session_id, None)
            self._cleaned_sessions[session_id] = session
            self.registry.remove(session_id)
            self._finalizing_sessions.discard(session_id)
        finally:
            self._cleanup_tasks.pop(session_id, None)

    def _automatic_action(self, legal: PvpLegalActions) -> PvpAction:
        candidates = legal.moves if not legal.forced_switch else legal.switches
        if not candidates:
            raise ValueError("Showdown reported no legal PvP action.")
        return self._random.choice(list(candidates))
