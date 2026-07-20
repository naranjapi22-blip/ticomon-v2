from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from uuid import UUID

from application.pvp.events import PvpEventTranslator
from application.pvp.models import PvpAction, PvpLegalActions
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
        random_source: random.Random | None = None,
    ) -> None:
        self.registry = registry or PvpSessionRegistry()
        self._creature_repository = creature_repository
        self._controller_factory = controller_factory or PokeEnvPvpController
        self._team_validator = team_validator or PvpTeamValidator()
        self._random = random_source or random.Random()
        self._action_waiters: dict[tuple[UUID, int], asyncio.Future[PvpAction]] = {}
        self._legal_actions: dict[tuple[UUID, int], PvpLegalActions] = {}
        self._event_handlers: dict[UUID, Callable[[str], Awaitable[None]]] = {}
        self._finish_handlers: dict[UUID, Callable[[object], Awaitable[None]]] = {}

    def challenge(self, initiator_id: int, opponent_id: int) -> PvpSession:
        return self.registry.create(initiator_id, opponent_id)

    async def select_team(
        self,
        session_id: UUID,
        trainer_id: int,
        collection_numbers: list[int] | tuple[int, ...],
    ) -> tuple:
        session = self.registry.get(session_id)
        if self._creature_repository is None:
            raise RuntimeError("PvP creature repository is not configured.")
        creatures = []
        for collection_number in collection_numbers:
            creature = await self._creature_repository.get_by_collection_number(
                trainer_id, collection_number
            )
            if creature.trainer_id != trainer_id:
                raise ValueError("You can only select your own creatures.")
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
    ) -> bool:
        session = self.registry.get(session_id)
        async with session.lock:
            ready = session.confirm_team(trainer_id)
            if not ready:
                return False
            selected = getattr(session, "selected_creatures", {})
            teams = {player_id: selected[player_id] for player_id in session.player_ids}
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
            controller = self._controller_factory()
            session.battle_controller = controller
            if on_event is not None:
                self._event_handlers[session_id] = on_event
            if on_finished is not None:
                self._finish_handlers[session_id] = on_finished
            session.begin_battle()

        callbacks = PvpControllerCallbacks(
            on_actions=lambda player_id, legal: self.request_action(
                session_id, player_id, legal
            ),
            on_protocol=lambda messages: self.handle_protocol(session_id, messages),
            on_finished=lambda battle: self.finish_from_controller(session_id, battle),
        )
        try:
            await controller.start(teams, callbacks)
        except Exception:
            await self.cleanup(session_id)
            raise
        return True

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
            self._action_waiters[key] = future
            self._legal_actions[key] = legal
            timeout = (
                FORCED_SWITCH_TIMEOUT_SECONDS
                if legal.forced_switch
                else ACTION_TIMEOUT_SECONDS
            )
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            action = self._automatic_action(legal)
            async with session.lock:
                session.choose_action(trainer_id, action.identifier)
                pending_actions = [
                    pending
                    for (pending_session_id, _), pending in self._action_waiters.items()
                    if pending_session_id == session_id
                ]
                if len(pending_actions) == 2 and all(
                    pending.done() for pending in pending_actions
                ):
                    session.begin_resolution()
            return action
        finally:
            self._action_waiters.pop(key, None)
            self._legal_actions.pop(key, None)

    async def submit_action(
        self,
        session_id: UUID,
        trainer_id: int,
        action: PvpAction,
    ) -> None:
        session = self.registry.get(session_id)
        async with session.lock:
            key = (session_id, trainer_id)
            legal = self._legal_actions.get(key)
            future = self._action_waiters.get(key)
            if legal is None or future is None or future.done():
                raise ValueError("This action window is no longer active.")
            if action.identifier not in {item.identifier for item in legal.all_actions}:
                raise ValueError("That action is not legal in the current state.")
            future.set_result(action)
            session.choose_action(trainer_id, action.identifier)
            pending_actions = [
                pending
                for (pending_session_id, _), pending in self._action_waiters.items()
                if pending_session_id == session_id
            ]
            if len(pending_actions) == 2 and all(
                pending.done() for pending in pending_actions
            ):
                session.begin_resolution()

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

    async def decline(self, session_id: UUID) -> None:
        session = self.registry.get(session_id)
        session.cancel()
        await self.cleanup(session_id)

    async def cleanup(self, session_id: UUID) -> None:
        try:
            session = self.registry.get(session_id)
        except ValueError:
            return
        for future in list(self._action_waiters.values()):
            if not future.done():
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
        controller = session.battle_controller
        if controller is not None:
            await controller.close()
        for task in list(session.timeout_tasks):
            if not task.done():
                task.cancel()
        session.timeout_tasks.clear()
        session.cancel()
        self._event_handlers.pop(session_id, None)
        self._finish_handlers.pop(session_id, None)
        self.registry.remove(session_id)

    def _automatic_action(self, legal: PvpLegalActions) -> PvpAction:
        candidates = legal.moves if not legal.forced_switch else legal.switches
        if not candidates:
            raise ValueError("Showdown reported no legal PvP action.")
        return self._random.choice(list(candidates))
