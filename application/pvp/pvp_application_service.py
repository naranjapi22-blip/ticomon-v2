from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from application.pvp.events import PvpEventTranslator
from application.pvp.models import PvpAction, PvpLegalActions
from application.pvp.snapshots import PvpBattleSnapshot
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

    def challenge(self, initiator_id: int, opponent_id: int) -> PvpSession:
        return self.registry.create(initiator_id, opponent_id)

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
                if len(refreshed) != len(team) or any(
                    creature.trainer_id != player_id for creature in refreshed
                ):
                    raise ValueError("A selected creature is no longer owned by you.")
                self._team_validator.validate(refreshed)
                session.selected_creatures[player_id] = tuple(refreshed)
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
            try:
                controller = self._controller_factory()
            except Exception:
                session.startup_claimed = False
                session.cancel()
                self.registry.remove(session_id)
                raise
            session.battle_controller = controller
            if on_event is not None:
                self._event_handlers[session_id] = on_event
            if on_finished is not None:
                self._finish_handlers[session_id] = on_finished
            if on_snapshot is not None:
                self._snapshot_handlers[session_id] = on_snapshot
            session.begin_battle()
            session.phase = PvpPhase.STARTING

        callbacks = PvpControllerCallbacks(
            on_actions=lambda player_id, legal: self.request_action(
                session_id, player_id, legal
            ),
            on_protocol=lambda messages: self.handle_protocol(session_id, messages),
            on_finished=lambda battle: self.finish_from_controller(session_id, battle),
            on_snapshot=lambda snapshot: self.handle_snapshot(session_id, snapshot),
            on_error=lambda error: self.handle_controller_error(session_id, error),
        )
        task = asyncio.create_task(
            self._start_controller(session_id, session, controller, teams, callbacks)
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
                "PvP startup failed",
                extra={
                    "session_id": str(session_id),
                    "session_state": session.phase.value,
                    "error_type": type(error).__name__,
                },
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
            "PvP controller task failed",
            extra={
                "session_id": str(session_id),
                "error_type": type(error).__name__,
            },
        )
        handler = self._event_handlers.get(session_id)
        if handler is not None:
            try:
                await handler("PvP ended unexpectedly and was cleaned up.")
            except Exception:
                logger.debug("Unable to publish PvP controller failure", exc_info=True)
        await self.cleanup(session_id)

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
            self._request_ids[key] = request_id
            session.register_action_request(trainer_id, request_id)
            timeout = (
                FORCED_SWITCH_TIMEOUT_SECONDS
                if legal.forced_switch
                else ACTION_TIMEOUT_SECONDS
            )
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
        except asyncio.TimeoutError:
            action = self._automatic_action(legal)
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
        await self.cleanup(session_id)

    async def handle_protocol(
        self, session_id: UUID, messages: list[list[str]]
    ) -> None:
        # Raw protocol is deliberately not rendered as history. The callback receives
        # only the current compact event and the board layer replaces the old one.
        translator = PvpEventTranslator()
        steps = translator.translate(messages)
        handler = self._event_handlers.get(session_id)
        if handler is not None:
            for step in steps:
                await handler(step.message)

    async def finish_from_controller(self, session_id: UUID, battle: object) -> None:
        handler = self._finish_handlers.get(session_id)
        if handler is not None:
            await handler(battle)
        await self.cleanup(session_id)

    async def handle_snapshot(
        self, session_id: UUID, snapshot: PvpBattleSnapshot
    ) -> None:
        handler = self._snapshot_handlers.get(session_id)
        if handler is not None:
            await handler(snapshot)

    async def decline(self, session_id: UUID) -> None:
        session = self.registry.get(session_id)
        session.cancel()
        await self.cleanup(session_id)

    async def cleanup(self, session_id: UUID) -> None:
        try:
            session = self.registry.get(session_id)
        except ValueError:
            return
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
        current_task = asyncio.current_task()
        tasks_to_cancel = [
            task
            for task in session.timeout_tasks
            if task is not current_task and not task.done()
        ]
        for task in tasks_to_cancel:
            task.cancel()
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        session.timeout_tasks.clear()
        session.startup_task = None
        session.startup_claimed = False
        controller = session.battle_controller
        if controller is not None:
            await controller.close()
        session.cancel()
        self._event_handlers.pop(session_id, None)
        self._finish_handlers.pop(session_id, None)
        self._snapshot_handlers.pop(session_id, None)
        self.registry.remove(session_id)

    def _automatic_action(self, legal: PvpLegalActions) -> PvpAction:
        candidates = legal.moves if not legal.forced_switch else legal.switches
        if not candidates:
            raise ValueError("Showdown reported no legal PvP action.")
        return self._random.choice(list(candidates))
