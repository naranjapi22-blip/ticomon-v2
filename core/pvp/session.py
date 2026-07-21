from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

ACTION_TIMEOUT_SECONDS = 15
FORCED_SWITCH_TIMEOUT_SECONDS = 10
MAX_PVP_TURNS = 100
MAX_PVP_DURATION_SECONDS = 1800


class PvpPhase(str, Enum):
    CHALLENGE = "challenge"
    TEAM_SELECTION = "team_selection"
    STARTING = "starting"
    WAITING_FOR_ACTIONS = "waiting_for_actions"
    RESOLVING = "resolving"
    FORCED_SWITCH = "forced_switch"
    FINISHED = "finished"
    CANCELLED = "cancelled"


@dataclass
class PvpSession:
    initiator_id: int
    opponent_id: int
    id: UUID = field(default_factory=uuid4)
    phase: PvpPhase = PvpPhase.CHALLENGE
    turn_number: int = 0
    selected_teams: dict[int, tuple[int, ...]] = field(default_factory=dict)
    selected_creatures: dict[int, tuple[object, ...]] = field(default_factory=dict)
    confirmed_teams: set[int] = field(default_factory=set)
    selected_actions: dict[int, str] = field(default_factory=dict)
    action_turn: int = 0
    message: object | None = field(default=None, repr=False)
    battle_controller: object | None = field(default=None, repr=False)
    timeout_tasks: set[asyncio.Task] = field(default_factory=set, repr=False)
    active_action_requests: dict[int, str] = field(default_factory=dict, repr=False)
    startup_claimed: bool = field(default=False, repr=False)
    startup_task: asyncio.Task | None = field(default=None, repr=False)
    started_monotonic: float | None = field(default=None, repr=False)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @property
    def player_ids(self) -> frozenset[int]:
        return frozenset((self.initiator_id, self.opponent_id))

    def select_team(
        self, trainer_id: int, creature_ids: list[int] | tuple[int, ...]
    ) -> None:
        self._require_player(trainer_id)
        if self.phase not in {
            PvpPhase.CHALLENGE,
            PvpPhase.TEAM_SELECTION,
            PvpPhase.WAITING_FOR_ACTIONS,
        }:
            raise ValueError("Team selection is no longer available.")
        ids = tuple(creature_ids)
        if len(ids) != 3 or len(set(ids)) != 3:
            raise ValueError("A PvP team must contain three different creatures.")
        self.selected_teams[trainer_id] = ids
        self.confirmed_teams.discard(trainer_id)
        self.phase = PvpPhase.TEAM_SELECTION
        if len(self.selected_teams) == 2:
            self.phase = PvpPhase.WAITING_FOR_ACTIONS

    def confirm_team(self, trainer_id: int) -> bool:
        self._require_player(trainer_id)
        team = self.selected_teams.get(trainer_id)
        if team is None or len(team) != 3:
            raise ValueError("Select exactly three creatures before confirming.")
        self.confirmed_teams.add(trainer_id)
        return len(self.confirmed_teams) == 2

    def begin_battle(self) -> None:
        if self.confirmed_teams != set(self.player_ids):
            raise ValueError("Both players must confirm their teams.")
        self.phase = PvpPhase.WAITING_FOR_ACTIONS
        self.turn_number = 1
        self.action_turn = self.turn_number
        self.started_monotonic = time.monotonic()

    def choose_action(self, trainer_id: int, action: str) -> bool:
        self._require_player(trainer_id)
        if self.phase not in {PvpPhase.WAITING_FOR_ACTIONS, PvpPhase.RESOLVING}:
            raise ValueError("The session is not accepting actions.")
        if not action:
            raise ValueError("An action is required.")
        self.selected_actions[trainer_id] = action
        self.action_turn = self.turn_number
        return len(self.selected_actions) == 2

    def register_action_request(self, trainer_id: int, request_id: str) -> None:
        self._require_player(trainer_id)
        if self.phase not in {PvpPhase.WAITING_FOR_ACTIONS, PvpPhase.FORCED_SWITCH}:
            raise ValueError("The session is not accepting actions.")
        self.active_action_requests[trainer_id] = request_id

    def try_choose_action(self, trainer_id: int, request_id: str, action: str) -> bool:
        if self.active_action_requests.get(trainer_id) != request_id:
            return False
        if self.phase not in {PvpPhase.WAITING_FOR_ACTIONS, PvpPhase.FORCED_SWITCH}:
            return False
        if not action:
            return False
        self.selected_actions[trainer_id] = action
        self.action_turn = self.turn_number
        self.active_action_requests.pop(trainer_id, None)
        return True

    def clear_actions(self) -> None:
        self.selected_actions.clear()
        self.active_action_requests.clear()

    def begin_turn_resolution(self) -> tuple[tuple[int, str], ...]:
        if self.phase != PvpPhase.WAITING_FOR_ACTIONS:
            raise ValueError("The session is not waiting for actions.")
        return self.begin_resolution()

    def next_turn(self) -> None:
        self.turn_number += 1
        self.action_turn = self.turn_number
        self.clear_actions()
        self.phase = PvpPhase.WAITING_FOR_ACTIONS

    def begin_resolution(self) -> tuple[tuple[int, str], ...]:
        if len(self.selected_actions) != 2:
            raise ValueError("Both players must choose an action.")
        self.phase = PvpPhase.RESOLVING
        return tuple(self.selected_actions.items())

    def finish(self) -> None:
        self.phase = PvpPhase.FINISHED
        self.active_action_requests.clear()

    def cancel(self) -> None:
        self.phase = PvpPhase.CANCELLED
        self.active_action_requests.clear()

    def _require_player(self, trainer_id: int) -> None:
        if trainer_id not in self.player_ids:
            raise ValueError("The trainer is not part of this PvP session.")


class PvpSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[UUID, PvpSession] = {}
        self._occupied: dict[int, UUID] = {}
        self._occupied_creatures: dict[int, UUID] = {}
        self._session_creatures: dict[UUID, set[int]] = {}

    def create(self, initiator_id: int, opponent_id: int) -> PvpSession:
        if initiator_id == opponent_id:
            raise ValueError("You cannot challenge yourself.")
        if initiator_id in self._occupied or opponent_id in self._occupied:
            raise ValueError("One of the trainers is already in a PvP session.")
        session = PvpSession(initiator_id, opponent_id)
        self._sessions[session.id] = session
        self._occupied[initiator_id] = session.id
        self._occupied[opponent_id] = session.id
        return session

    def get(self, session_id: UUID) -> PvpSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise ValueError("PvP session was not found.") from error

    def is_occupied(self, trainer_id: int) -> bool:
        return trainer_id in self._occupied

    def reserve_creatures(
        self, session_id: UUID, creature_ids: list[int] | tuple[int, ...]
    ) -> None:
        if len(set(creature_ids)) != len(creature_ids):
            raise ValueError("A creature cannot be selected twice in one PvP battle.")
        for creature_id in creature_ids:
            owner = self._occupied_creatures.get(creature_id)
            if owner is not None and owner != session_id:
                raise ValueError("A selected creature is already in a PvP session.")
        previous = self._session_creatures.setdefault(session_id, set())
        for creature_id in previous:
            self._occupied_creatures.pop(creature_id, None)
        previous.clear()
        for creature_id in creature_ids:
            self._occupied_creatures[creature_id] = session_id
            previous.add(creature_id)

    def release_creatures(self, session_id: UUID) -> None:
        for creature_id, owner in list(self._occupied_creatures.items()):
            if owner == session_id:
                self._occupied_creatures.pop(creature_id, None)
        self._session_creatures.pop(session_id, None)

    def remove(self, session_id: UUID) -> None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        self.release_creatures(session_id)
        for trainer_id in session.player_ids:
            self._occupied.pop(trainer_id, None)
