from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

ACTION_TIMEOUT_SECONDS = 15
FORCED_SWITCH_TIMEOUT_SECONDS = 10


class PvpPhase(str, Enum):
    CHALLENGE = "challenge"
    TEAM_SELECTION = "team_selection"
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
    selected_actions: dict[int, str] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @property
    def player_ids(self) -> frozenset[int]:
        return frozenset((self.initiator_id, self.opponent_id))

    def select_team(
        self, trainer_id: int, creature_ids: list[int] | tuple[int, ...]
    ) -> None:
        self._require_player(trainer_id)
        if self.phase not in {PvpPhase.CHALLENGE, PvpPhase.TEAM_SELECTION}:
            raise ValueError("Team selection is no longer available.")
        ids = tuple(creature_ids)
        if len(ids) != 3 or len(set(ids)) != 3:
            raise ValueError("A PvP team must contain three different creatures.")
        self.selected_teams[trainer_id] = ids
        self.phase = PvpPhase.TEAM_SELECTION
        if len(self.selected_teams) == 2:
            self.phase = PvpPhase.WAITING_FOR_ACTIONS

    def choose_action(self, trainer_id: int, action: str) -> bool:
        self._require_player(trainer_id)
        if self.phase != PvpPhase.WAITING_FOR_ACTIONS:
            raise ValueError("The session is not accepting actions.")
        if not action:
            raise ValueError("An action is required.")
        self.selected_actions[trainer_id] = action
        return len(self.selected_actions) == 2

    def begin_resolution(self) -> tuple[tuple[int, str], ...]:
        if len(self.selected_actions) != 2:
            raise ValueError("Both players must choose an action.")
        self.phase = PvpPhase.RESOLVING
        return tuple(self.selected_actions.items())

    def finish(self) -> None:
        self.phase = PvpPhase.FINISHED

    def cancel(self) -> None:
        self.phase = PvpPhase.CANCELLED

    def _require_player(self, trainer_id: int) -> None:
        if trainer_id not in self.player_ids:
            raise ValueError("The trainer is not part of this PvP session.")


class PvpSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[UUID, PvpSession] = {}
        self._occupied: dict[int, UUID] = {}

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

    def remove(self, session_id: UUID) -> None:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        for trainer_id in session.player_ids:
            self._occupied.pop(trainer_id, None)
